"""INSP MAP(검사 맵) 조회 — 범용 조회 계층.

MCRS 발생 여부와 무관하게 동작한다. MCRS 가 있으면 해당 슬롯에 표시가 붙을 뿐이다.

담당 기능:
- 지정한 공정의 INSP MAP — Lot 의 전체 슬롯
- 같은 Lot/슬롯이 지나온 과거 검사 공정의 MAP (이어보기)
- 같은 장비를 지나간 다른 device/공정의 검사 실적

이미지 자체는 이 계층에서 바이트로 다루지 않는다. 참조(URL)만 만들고 실제 렌더링은
호출한 쪽이 담당한다 — LLM 컨텍스트에 이미지 데이터가 들어가면 토큰이 폭발한다.
"""
from __future__ import annotations

import random
from datetime import timedelta

from core.errors import ToolError

from . import context, mcrs

# TODO: 가이아2.0 의 이미지 서빙 규약에 맞게 교체.
#       이미지 참조 생성을 이 함수 하나로 모아두어 규약이 바뀌어도 여기만 고치면 되게 한다.
_IMAGE_BASE = "/api/mcrs/image"


def insp_map_url(lot_id: str, step_id: str, slot_no: int) -> str:
    return f"{_IMAGE_BASE}/insp-map?lot_id={lot_id}&step_id={step_id}&slot={slot_no}"


def get_insp_map(lot_id: str, step_id: str) -> dict:
    """지정한 공정의 INSP MAP 을 Lot 의 전체 슬롯에 대해 반환한다.

    MCRS 가 있으면 해당 슬롯이 표시되고, 없으면 전 슬롯이 기준선 수준으로 나온다.
    한 슬롯만 튀는지 Lot 전체가 나쁜지가 원인 판별의 첫 갈림길이라 항상 전 슬롯을 준다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    issue = ctx["mcrs"]
    baseline = context.step_baseline(ctx)
    rng = random.Random(context.seed(ctx["lot_id"], ctx["step_id"], "inspmap"))

    slots = []
    for slot_no in range(1, ctx["slot_count"] + 1):
        is_target = bool(issue) and slot_no == issue["slot_no"]
        if is_target:
            defect_count = issue["defect_count"]
        else:
            # MCRS 슬롯 인접은 조금 더 높게 — 슬롯 위치 상관성을 보기 위한 mock
            adjacency = (
                1.6 if issue and abs(slot_no - issue["slot_no"]) <= 2 else 1.0
            )
            defect_count = int(baseline * adjacency * rng.uniform(0.6, 1.4))
        slots.append(
            {
                "slot_no": slot_no,
                "defect_count": defect_count,
                "is_mcrs_slot": is_target,
                "image_url": insp_map_url(ctx["lot_id"], ctx["step_id"], slot_no),
            }
        )

    others = [s["defect_count"] for s in slots if not s["is_mcrs_slot"]]
    return {
        "ctx": ctx,
        "slots": slots,
        "baseline": baseline,
        "others_mean": round(sum(others) / len(others), 1) if others else 0.0,
        "others_max": max(others) if others else 0,
    }


def get_insp_map_history(lot_id: str, step_id: str, slot_no: int | None = None) -> dict:
    """같은 Lot/슬롯이 지나온 과거 검사 공정의 MAP 을 오래된 순으로 반환한다.

    대상 공정은 MCRS 이슈가 아니라 **공정 이력**에서 뽑으므로, MCRS 가 나지 않은
    공정도 포함된다. "이 슬롯이 원래부터 나빴는지" 를 보려면 그래야 한다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    slot = mcrs.target_slot(ctx, slot_no)
    rng = random.Random(context.seed(ctx["lot_id"], "history", slot))

    timeline = []
    for past in context.prior_steps(ctx):
        past_ctx = mcrs.resolve(ctx["lot_id"], past["step_id"])
        past_issue = past_ctx["mcrs"]
        # "그 공정에 MCRS 가 있었다" 와 "추적 중인 이 슬롯이 MCRS 슬롯이다" 는 다르다.
        # 둘을 구분하지 않으면 다른 슬롯의 MCRS 를 이 슬롯 것으로 오독하게 된다.
        slot_has_mcrs = bool(past_issue) and past_issue["slot_no"] == slot
        if slot_has_mcrs:
            defect_count = past_issue["defect_count"]
        else:
            defect_count = int(context.step_baseline(past_ctx) * rng.uniform(0.4, 1.2))
        timeline.append(
            {
                "step_id": past["step_id"],
                "step_desc": past["step_desc"],
                "eq_id": past["eq_id"],
                "inspected_at": past["processed_at"],
                "defect_count": defect_count,
                "slot_has_mcrs": slot_has_mcrs,
                "step_mcrs_slot": past_issue["slot_no"] if past_issue else None,
                "image_url": insp_map_url(ctx["lot_id"], past["step_id"], slot),
            }
        )

    current = get_insp_map(lot_id, step_id)
    current_slot = next(s for s in current["slots"] if s["slot_no"] == slot)
    timeline.append(
        {
            "step_id": ctx["step_id"],
            "step_desc": ctx["step_desc"],
            "eq_id": ctx["eq_id"],
            "inspected_at": ctx["processed_at"],
            "defect_count": current_slot["defect_count"],
            "slot_has_mcrs": current_slot["is_mcrs_slot"],
            "step_mcrs_slot": ctx["mcrs"]["slot_no"] if ctx["mcrs"] else None,
            "image_url": insp_map_url(ctx["lot_id"], ctx["step_id"], slot),
            "is_current": True,
        }
    )

    return {"ctx": ctx, "slot_no": slot, "timeline": timeline}


def get_eq_insp_coverage(lot_id: str, step_id: str, days: int = 30) -> dict:
    """해당 공정을 처리한 장비를 지나간 '다른 device / 다른 공정' 의 검사 실적.

    장비 자체의 문제인지, 이 device/공정 조합에만 나타나는 문제인지 가르는 근거다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    if days < 1 or days > 180:
        raise ToolError("조회 실패: 조회 기간(days)은 1~180 사이여야 합니다.")

    rng = random.Random(context.seed(ctx["eq_id"], "coverage", days))
    ref = context.parse_processed_at(ctx)
    baseline = context.step_baseline(ctx)

    # TODO: 실제로는 장비 이력 테이블에서 기간 내 처리된 device/step 조합을 조회.
    other_devices = ["D7Y-256G", "D5X-128G", "D9Z-512G"]
    other_steps = ["INSP-CMP-01", "INSP-CMP-02"]

    rows = []
    for device_id in other_devices:
        for other_step in other_steps:
            if device_id == ctx["device_id"] and other_step == ctx["step_id"]:
                continue  # 조회 대상 조합 자신은 제외
            lot_count = rng.randint(0, 9)
            if lot_count == 0:
                continue  # 기간 내 검사 실적 없음
            mean_defect = round(baseline * rng.uniform(0.5, 2.4), 1)
            rows.append(
                {
                    "device_id": device_id,
                    "step_id": other_step,
                    "lot_count": lot_count,
                    "mean_defect": mean_defect,
                    "last_inspected_at": (
                        ref - timedelta(hours=rng.randint(2, days * 24))
                    ).strftime("%Y-%m-%d %H:%M"),
                    # 기준선의 2배를 넘으면 같이 이상한 것으로 표시
                    "abnormal": mean_defect > baseline * 2,
                }
            )

    return {
        "ctx": ctx,
        "days": days,
        "baseline": baseline,
        "rows": sorted(rows, key=lambda r: r["mean_defect"], reverse=True),
        "abnormal_count": sum(1 for r in rows if r["abnormal"]),
    }
