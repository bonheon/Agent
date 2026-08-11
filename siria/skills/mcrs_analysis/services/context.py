"""공정 이력 기반 컨텍스트 해결 — 범용 조회 계층의 기반.

Lot 이 어떤 공정을 지나갔으면 장비·device 는 **공정 이력에 항상 남는다.** MCRS 발생
여부와 무관하다. 그래서 "이 Lot 의 이 공정" 을 특정하는 근거는 공정 이력이고,
MCRS 이슈는 그 위에 얹히는 보강 정보다 (`mcrs.resolve` 참고).

이 계층을 분리하기 전에는 MCRS 이슈 테이블에서 장비를 찾았고, 그래서 MCRS 가 없는
Lot 은 INSP MAP 조회조차 막혔다. 조회 tool 은 MCRS 와 무관하게 동작해야 한다.
"""
from __future__ import annotations

import random
import re
import zlib
from datetime import datetime, timedelta

from core.errors import ToolError

# TODO: 사내 Lot 번호 체계에 맞게 수정. 지금은 영숫자 6~12자만 허용.
_LOT_PATTERN = re.compile(r"^[A-Z0-9]{6,12}$")

# Lot 당 슬롯 수. TODO: 실제로는 Lot 별로 다르므로 공정 이력에서 가져올 것.
SLOTS_PER_LOT = 25

# 기준 시각 이후 며칠치 데이터를 함께 생성할지 (trend / PM 전후 비교용).
POST_DAYS = 5

# TODO: mock 제거하고 실제 공정 이력(라우팅) 테이블 조회로 교체.
#       (lot_id, step_id) → 장비·device·처리시각 이 조회의 단일 근거다.
_MOCK_ROUTING: dict[str, list[dict]] = {
    "TE2FE35": [
        {
            "step_id": "INSP-PHOTO-02",
            "step_desc": "Photo 2층 후 검사",
            "eq_id": "PHO-305",
            "device_id": "D5X-128G",
            "processed_at": "2026-08-09 15:05:00",
        },
        {
            "step_id": "INSP-ETCH-03",
            "step_desc": "Etch 3층 후 검사",
            "eq_id": "ETC-118",
            "device_id": "D5X-128G",
            "processed_at": "2026-08-09 21:40:00",
        },
        {
            "step_id": "INSP-CMP-01",
            "step_desc": "CMP 후 검사",
            "eq_id": "CMP-201",
            "device_id": "D5X-128G",
            "processed_at": "2026-08-10 04:12:00",
        },
        # MCRS 가 나지 않은 공정 — 범용 조회가 되는지 확인하는 용도
        {
            "step_id": "INSP-CMP-02",
            "step_desc": "CMP 2차 검사",
            "eq_id": "CMP-203",
            "device_id": "D5X-128G",
            "processed_at": "2026-08-10 11:30:00",
        },
    ],
    "TE2FE36": [
        {
            "step_id": "INSP-CMP-01",
            "step_desc": "CMP 후 검사",
            "eq_id": "CMP-201",
            "device_id": "D7Y-256G",
            "processed_at": "2026-08-11 02:20:00",
        },
    ],
    # MCRS 가 전혀 없는 정상 Lot
    "TE2FE40": [
        {
            "step_id": "INSP-PHOTO-02",
            "step_desc": "Photo 2층 후 검사",
            "eq_id": "PHO-305",
            "device_id": "D9Z-512G",
            "processed_at": "2026-08-08 13:20:00",
        },
        {
            "step_id": "INSP-CMP-01",
            "step_desc": "CMP 후 검사",
            "eq_id": "CMP-201",
            "device_id": "D9Z-512G",
            "processed_at": "2026-08-08 22:45:00",
        },
    ],
}


def seed(*parts: object) -> int:
    """mock 데이터용 결정론적 시드.

    파이썬 내장 hash() 는 문자열에 대해 프로세스마다 값이 바뀌므로(PYTHONHASHSEED)
    mock 재현성이 깨진다. crc32 를 쓴다.
    """
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return zlib.crc32(key)


def day_of(moment: datetime) -> datetime:
    """자정으로 내린 날짜. 일 단위 집계와 구간 분류의 기준을 하나로 맞춘다."""
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize_lot_id(lot_id: str) -> str:
    lot_id = (lot_id or "").strip().upper()
    if not _LOT_PATTERN.match(lot_id):
        raise ToolError(
            "조회 실패: Lot 번호 형식을 확인하세요 (예: TE2FE35). "
            "사용자에게 정확한 Lot 번호를 다시 물어보세요."
        )
    return lot_id


def get_route(lot_id: str) -> list[dict]:
    """Lot 이 지나온 검사 공정 목록을 시간 순으로 반환한다."""
    lot_id = normalize_lot_id(lot_id)
    steps = _MOCK_ROUTING.get(lot_id)
    if steps is None:
        raise ToolError(
            f"조회 실패: '{lot_id}' 의 공정 이력이 없습니다. Lot 번호를 확인하세요."
        )
    return sorted(steps, key=lambda s: s["processed_at"])


def resolve_context(lot_id: str, step_id: str) -> dict:
    """(Lot, 공정) 으로 장비·device·처리시각을 특정한다.

    MCRS 발생 여부와 무관하게 동작한다. MCRS 보강이 필요하면 `mcrs.resolve` 를 쓴다.
    """
    steps = get_route(lot_id)
    normalized_step = (step_id or "").strip().upper()

    for step in steps:
        if step["step_id"].upper() == normalized_step:
            return {
                "lot_id": normalize_lot_id(lot_id),
                "slot_count": SLOTS_PER_LOT,
                "mcrs": None,  # mcrs.resolve 가 채운다
                **step,
            }

    available = ", ".join(s["step_id"] for s in steps)
    raise ToolError(
        f"조회 실패: '{normalize_lot_id(lot_id)}' 은 공정 '{normalized_step}' 를 "
        f"지나간 이력이 없습니다. 이 Lot 이 지나간 공정: {available}"
    )


def parse_processed_at(ctx: dict) -> datetime:
    return datetime.strptime(ctx["processed_at"], "%Y-%m-%d %H:%M:%S")


def prior_steps(ctx: dict) -> list[dict]:
    """해당 공정 이전에 같은 Lot 이 지나온 검사 공정 (오래된 순).

    MCRS 이슈가 아니라 공정 이력에서 뽑으므로, MCRS 가 없는 공정도 포함된다.
    """
    base = ctx["processed_at"]
    return [s for s in get_route(ctx["lot_id"]) if s["processed_at"] < base]


def step_baseline(ctx: dict) -> float:
    """해당 공정/device 의 평상시 defect 수준. MCRS 가 없을 때의 기준선이 된다."""
    rng = random.Random(seed(ctx["step_id"], ctx["device_id"], "baseline"))
    return round(rng.uniform(22.0, 45.0), 1)


def mock_time_series(ctx: dict, days: int) -> list[tuple[datetime, float, int]]:
    """(날짜, 평균 defect, 측정 건수) 시계열 mock.

    trend 조회와 PM 전후 비교가 같은 데이터를 봐야 하므로 여기서 한 번만 생성한다.
    MCRS 가 있으면 발생일부터 급증했다가 서서히 내려오고, 없으면 기준선에서 진동한다.

    TODO: 실제 검사 결과 이력 테이블 조회로 교체.
    """
    issue = ctx.get("mcrs")
    rng = random.Random(seed(ctx["lot_id"], ctx["step_id"], "trend", days))
    ref_day = day_of(parse_processed_at(ctx))
    baseline = step_baseline(ctx)

    series: list[tuple[datetime, float, int]] = []

    for offset in range(days, 0, -1):
        day = ref_day - timedelta(days=offset)
        series.append((day, round(baseline * rng.uniform(0.7, 1.35), 1), rng.randint(2, 6)))

    for offset in range(0, POST_DAYS + 1):
        day = ref_day + timedelta(days=offset)
        if issue:
            decay = max(0.35, 1.0 - offset * 0.15)
            level = issue["defect_count"] * decay * rng.uniform(0.85, 1.1)
        else:
            level = baseline * rng.uniform(0.7, 1.35)
        series.append((day, round(level, 1), rng.randint(2, 6)))

    return series
