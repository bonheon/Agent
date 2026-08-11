"""MCRS 이슈 조회 비즈니스 로직.

순수 파이썬 — LangChain/LangGraph 의존 없음.

이 모듈의 핵심은 `resolve_issue()` 다. MCRS 분석의 모든 후속 조회(INSP MAP,
REV 이미지, PM 이력, trend, 교차 확인)는 "어느 Lot 의 어느 공정" 하나만 정해지면
장비/슬롯/device/발생시각이 전부 따라 결정된다. 그래서 후속 tool 들은
(lot_id, step_id) 만 인자로 받고, 나머지는 여기서 되찾는다.

이렇게 하지 않으면 LLM 이 eq_id 나 slot_no 를 직접 넘겨야 하는데, 아직 조회하지
않은 값을 지어내서 넘기는 사고가 난다.
"""
from __future__ import annotations

import re
import zlib
from datetime import datetime, timedelta

from core.errors import ToolError

# TODO: 사내 Lot 번호 체계에 맞게 수정. 지금은 영숫자 6~12자만 허용.
_LOT_PATTERN = re.compile(r"^[A-Z0-9]{6,12}$")

# TODO: mock 제거하고 실제 MCRS 이슈 테이블 조회(core/db.py)로 교체.
#       아래 dict 의 key 구성이 곧 후속 tool 들이 의존하는 계약이므로,
#       실 DB 로 바꿀 때 key 이름과 의미는 그대로 유지할 것.
_MOCK_ISSUES: dict[str, list[dict]] = {
    "TE2FE35": [
        {
            "issue_id": "MC-20260810-001",
            "lot_id": "TE2FE35",
            "step_id": "INSP-CMP-01",
            "step_desc": "CMP 후 검사",
            "eq_id": "CMP-201",
            "device_id": "D5X-128G",
            "slot_no": 12,
            "defect_count": 142,
            "mcrs_code": "MCRS-SCRATCH",
            "detected_at": "2026-08-10 04:12:00",
        },
        {
            "issue_id": "MC-20260810-002",
            "lot_id": "TE2FE35",
            "step_id": "INSP-ETCH-03",
            "step_desc": "Etch 3층 후 검사",
            "eq_id": "ETC-118",
            "device_id": "D5X-128G",
            "slot_no": 7,
            "defect_count": 61,
            "mcrs_code": "MCRS-PARTICLE",
            "detected_at": "2026-08-09 21:40:00",
        },
        {
            "issue_id": "MC-20260810-003",
            "lot_id": "TE2FE35",
            "step_id": "INSP-PHOTO-02",
            "step_desc": "Photo 2층 후 검사",
            "eq_id": "PHO-305",
            "device_id": "D5X-128G",
            "slot_no": 12,
            "defect_count": 33,
            "mcrs_code": "MCRS-RESIDUE",
            "detected_at": "2026-08-09 15:05:00",
        },
    ],
    "TE2FE36": [
        {
            "issue_id": "MC-20260811-001",
            "lot_id": "TE2FE36",
            "step_id": "INSP-CMP-01",
            "step_desc": "CMP 후 검사",
            "eq_id": "CMP-201",
            "device_id": "D7Y-256G",
            "slot_no": 3,
            "defect_count": 97,
            "mcrs_code": "MCRS-SCRATCH",
            "detected_at": "2026-08-11 02:20:00",
        },
    ],
}

# Lot 당 슬롯 수. TODO: 실제로는 Lot 별로 다르므로 DB 에서 가져올 것.
SLOTS_PER_LOT = 25


def seed(*parts: object) -> int:
    """mock 데이터용 결정론적 시드.

    파이썬의 내장 hash() 는 문자열에 대해 프로세스마다 값이 바뀌므로
    (PYTHONHASHSEED) mock 재현성이 깨진다. crc32 를 쓴다.
    """
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return zlib.crc32(key)


def normalize_lot_id(lot_id: str) -> str:
    lot_id = (lot_id or "").strip().upper()
    if not _LOT_PATTERN.match(lot_id):
        raise ToolError(
            "조회 실패: Lot 번호 형식을 확인하세요 (예: TE2FE35). "
            "사용자에게 정확한 Lot 번호를 다시 물어보세요."
        )
    return lot_id


def get_mcrs_issues(lot_id: str) -> list[dict]:
    """Lot 1개에서 발생한 MCRS 이슈 목록을 발생 시각 내림차순으로 반환한다."""
    lot_id = normalize_lot_id(lot_id)

    issues = _MOCK_ISSUES.get(lot_id)
    if not issues:
        raise ToolError(
            f"조회 실패: '{lot_id}' 에 등록된 MCRS 이슈가 없습니다. "
            "Lot 번호가 맞는지, 조회 기간이 맞는지 사용자에게 확인하세요."
        )
    return sorted(issues, key=lambda i: i["detected_at"], reverse=True)


def resolve_issue(lot_id: str, step_id: str) -> dict:
    """(Lot, 공정) 으로 MCRS 이슈 1건을 특정한다.

    후속 조회 tool 들이 장비/슬롯/device/발생시각을 얻는 단일 경로.
    """
    issues = get_mcrs_issues(lot_id)
    step_id = (step_id or "").strip().upper()

    for issue in issues:
        if issue["step_id"].upper() == step_id:
            return issue

    available = ", ".join(i["step_id"] for i in issues)
    raise ToolError(
        f"조회 실패: '{lot_id}' 의 MCRS 이슈 중 공정 '{step_id}' 는 없습니다. "
        f"가능한 공정: {available}. 사용자에게 이 중 어느 공정인지 다시 물어보세요."
    )


def parse_detected_at(issue: dict) -> datetime:
    return datetime.strptime(issue["detected_at"], "%Y-%m-%d %H:%M:%S")


def prior_insp_steps(issue: dict) -> list[dict]:
    """해당 이슈 공정 이전에 같은 Lot 이 지나온 검사 공정 목록 (오래된 순).

    9번 기능(과거 INSP MAP 이어보기)의 대상 공정을 정한다.

    TODO: 실제로는 Lot 의 공정 이력(라우팅) 테이블에서 현재 step 이전의
          검사 step 을 뽑아야 한다. 지금은 같은 Lot 의 MCRS 이슈 공정만 사용.
    """
    base_time = parse_detected_at(issue)
    earlier = [
        i
        for i in get_mcrs_issues(issue["lot_id"])
        if parse_detected_at(i) < base_time
    ]
    return sorted(earlier, key=parse_detected_at)


# MCRS 발생 이후 며칠치를 함께 생성할지. 8번(PM 전후 비교)의 "MCRS 이후" 구간이
# 비지 않으려면 발생일 이후 데이터가 반드시 있어야 한다.
POST_MCRS_DAYS = 5


def day_of(moment: datetime) -> datetime:
    """자정으로 내린 날짜. 일 단위 집계와 구간 분류의 기준을 하나로 맞춘다."""
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def mock_time_series(issue: dict, days: int) -> list[tuple[datetime, float, int]]:
    """(날짜, 평균 defect, 측정 건수) 시계열 mock.

    7번(30일 trend)과 8번(PM 전후 비교)이 같은 데이터를 봐야 하므로 여기서 한 번만
    생성한다. 발생일 **이후** POST_MCRS_DAYS 일치도 함께 생성한다.

    TODO: 실제 검사 결과 이력 테이블 조회로 교체.
    """
    import random

    rng = random.Random(seed(issue["issue_id"], "trend", days))
    detected_day = day_of(parse_detected_at(issue))
    baseline = issue["defect_count"] * 0.28

    series: list[tuple[datetime, float, int]] = []

    # 발생 이전: 기준선 수준에서 진동
    for offset in range(days, 0, -1):
        day = detected_day - timedelta(days=offset)
        level = baseline * rng.uniform(0.7, 1.35)
        series.append((day, round(level, 1), rng.randint(2, 6)))

    # 발생일 이후: 급증한 뒤 서서히 내려오는 형태
    for offset in range(0, POST_MCRS_DAYS + 1):
        day = detected_day + timedelta(days=offset)
        decay = max(0.35, 1.0 - offset * 0.15)
        level = issue["defect_count"] * decay * rng.uniform(0.85, 1.1)
        series.append((day, round(level, 1), rng.randint(2, 6)))

    return series
