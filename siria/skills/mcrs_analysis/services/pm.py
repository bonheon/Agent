"""PM 이력 / 공정 trend / PM 전후 비교.

- get_pm_history, get_step_trend : 범용 조회 계층. MCRS 없이도 동작한다.
- compare_pm_effect             : 분석 계층. MCRS 가 있으면 구간을 3개로 나눠
                                  비교하고, 없으면 PM 전/후 2구간으로 비교한다.

PM 전후 비교는 의도적으로 여기서 '계산까지' 끝낸다. 30일치 원본을 LLM 에 넘겨서
평균을 내라고 시키면 토큰만 쓰고 계산도 틀린다. 구간별 통계만 넘긴다.
"""
from __future__ import annotations

import random
import statistics
from datetime import datetime, timedelta

from core.errors import ToolError

from . import context, mcrs

MAX_TREND_DAYS = 180


def get_pm_history(lot_id: str, step_id: str, days: int = 90) -> dict:
    """해당 공정을 처리한 장비의 PM 이력을 최근 순으로 반환한다.

    기준 시각(MCRS 가 있으면 발생 시각, 없으면 공정 처리 시각)에서 직전 PM 까지
    며칠 지났는지를 함께 계산한다 — PM 전후 판정의 기준선이 된다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    if days < 1 or days > 365:
        raise ToolError("조회 실패: PM 이력 조회 기간(days)은 1~365 사이여야 합니다.")

    ref = context.parse_processed_at(ctx)
    rng = random.Random(context.seed(ctx["eq_id"], "pm", days))

    # TODO: 실제 PM 이력 테이블 조회로 교체.
    #       정기 PM 주기는 장비 종류마다 다르므로 DB 에서 가져와야 한다.
    cycle_days = rng.choice([14, 21, 30])
    records = []
    cursor = ref - timedelta(days=rng.uniform(3.0, 6.0))
    while (ref - cursor).days <= days:
        records.append(
            {
                "pm_id": f"PM-{cursor:%Y%m%d}-{rng.randint(1, 9)}",
                "eq_id": ctx["eq_id"],
                "pm_type": rng.choice(["정기 PM", "정기 PM", "정기 PM", "긴급 PM"]),
                "started_at": cursor.strftime("%Y-%m-%d %H:%M"),
                "duration_h": round(rng.uniform(2.0, 9.0), 1),
                "main_work": rng.choice(
                    ["Pad 교체", "Slurry 라인 세정", "Chamber 세정", "Belt 교체", "파티클 점검"]
                ),
            }
        )
        cursor -= timedelta(days=cycle_days)

    if not records:
        raise ToolError(
            f"조회 실패: 장비 '{ctx['eq_id']}' 의 최근 {days}일 PM 이력이 없습니다. "
            "조회 기간을 늘려서 다시 시도해 보세요."
        )

    last_pm = records[0]
    last_pm_dt = datetime.strptime(last_pm["started_at"], "%Y-%m-%d %H:%M")
    return {
        "ctx": ctx,
        "eq_id": ctx["eq_id"],
        "days": days,
        "records": records,
        "last_pm": last_pm,
        "days_since_last_pm": round((ref - last_pm_dt).total_seconds() / 86400, 1),
        "pm_cycle_days": cycle_days,
    }


def get_step_trend(lot_id: str, step_id: str, days: int = 30) -> dict:
    """해당 공정의 최근 N일 검사 데이터를 일 단위로 반환한다 (trend 작성용)."""
    ctx = mcrs.resolve(lot_id, step_id)
    if days < 1 or days > MAX_TREND_DAYS:
        raise ToolError(
            f"조회 실패: trend 조회 기간(days)은 1~{MAX_TREND_DAYS} 사이여야 합니다."
        )

    points = [
        {
            "date": day.strftime("%Y-%m-%d"),
            "mean_defect": mean_defect,
            "sample_count": sample_count,
        }
        for day, mean_defect, sample_count in context.mock_time_series(ctx, days)
    ]

    return {
        "ctx": ctx,
        "days": days,
        "baseline": context.step_baseline(ctx),
        "points": points,
        "summary": _describe([p["mean_defect"] for p in points]),
    }


def compare_pm_effect(lot_id: str, step_id: str, days: int = 30) -> dict:
    """직전 PM 시점을 기준으로 데이터를 구간별로 나눠 비교한다.

    MCRS 가 있으면 3구간:
      1) PM 이전         — 원래 이 장비가 어느 수준이었는지 (기준선)
      2) PM 이후~MCRS 전 — PM 이 정상적으로 됐는지 (여기가 나쁘면 PM 자체가 의심)
      3) MCRS 이후       — 지금도 계속 나쁜지, 일시적이었는지

    MCRS 가 없으면 2구간(PM 이전 / PM 이후)으로 비교한다.

    판정 자체는 하지 않고 근거만 만든다. 최종 판단은 호출한 LLM 이 절차에 따라 한다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    pm = get_pm_history(lot_id, step_id)
    trend = get_step_trend(lot_id, step_id, days=days)

    # 구간 분류는 날짜(자정 기준) 단위로 한다. 시각까지 비교하면 MCRS 가 발생한 그날의
    # 급증값이 'PM 이후~MCRS 전' 구간에 섞여 들어가 비교가 오염된다.
    pm_day = context.day_of(
        datetime.strptime(pm["last_pm"]["started_at"], "%Y-%m-%d %H:%M")
    )
    ref_day = context.day_of(context.parse_processed_at(ctx))
    has_mcrs = bool(ctx["mcrs"])

    before_pm: list[float] = []
    after_pm: list[float] = []
    after_ref: list[float] = []
    for point in trend["points"]:
        day = datetime.strptime(point["date"], "%Y-%m-%d")
        value = point["mean_defect"]
        if day < pm_day:
            before_pm.append(value)
        elif has_mcrs and day >= ref_day:
            # 발생 당일 포함 — 급증이 시작된 날이므로 '이후' 구간에 넣는다.
            after_ref.append(value)
        else:
            after_pm.append(value)

    windows = {
        "before_pm": _describe(before_pm),
        "after_pm": _describe(after_pm),
    }
    if has_mcrs:
        windows["after_mcrs"] = _describe(after_ref)

    return {
        "ctx": ctx,
        "has_mcrs": has_mcrs,
        "last_pm": pm["last_pm"],
        "days_since_last_pm": pm["days_since_last_pm"],
        "pm_cycle_days": pm["pm_cycle_days"],
        "reference_at": ctx["processed_at"],
        "windows": windows,
    }


def _describe(values: list[float]) -> dict:
    """구간 통계. 값이 없으면 count=0 으로만 표시한다 (0.0 으로 채우지 않는다)."""
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 1),
        "std": round(statistics.pstdev(values), 1) if len(values) > 1 else 0.0,
        "min": round(min(values), 1),
        "max": round(max(values), 1),
    }
