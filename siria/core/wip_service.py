"""재공(WIP) 집계 비즈니스 로직 — 스텁.

순수 파이썬 — 프레임워크 의존 없음.
"""
from core.errors import ToolError


def get_wip_summary(area: str) -> list[dict]:
    """공정 area(예: PHOTO, ETCH) 기준 step 별 재공 Lot 수/수량 집계를 반환한다.

    TODO: 구현 — area 유효성 검증 후 core/db.py 로 집계 조회.
    """
    raise ToolError("조회 실패: 재공 집계 조회는 아직 구현되지 않은 기능입니다.")
