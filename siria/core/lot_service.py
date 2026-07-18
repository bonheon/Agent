"""Lot 조회 비즈니스 로직.

순수 파이썬 — LangChain/LangGraph 의존 없음. 같은 함수를 LangGraph tool,
MCP 서버, langflow 컴포넌트 어디서든 재사용한다.
"""
import re

from core.errors import ToolError

_LOT_PATTERN = re.compile(r"^LOT\d{4}[A-Z]\d{3}$")  # 예: LOT2401A001

# TODO: mock 데이터 제거하고 실제 DB 조회(core/db.py)로 교체
_MOCK_LOTS = {
    "LOT2401A001": {
        "lot_id": "LOT2401A001",
        "product": "PRD-128G-V2",
        "step": "PHOTO-3200",
        "step_desc": "Photo 3층 노광",
        "eq_id": "PHO-301",
        "qty": 25,
        "status": "RUN",
        "hold": False,
        "hold_reason": None,
        "last_event_time": "2026-07-18 09:32:00",
    },
    "LOT2401A002": {
        "lot_id": "LOT2401A002",
        "product": "PRD-128G-V2",
        "step": "ETCH-4100",
        "step_desc": "Etch 4층 식각",
        "eq_id": None,
        "qty": 24,
        "status": "HOLD",
        "hold": True,
        "hold_reason": "SPC OOC — CD 측정치 상한 초과",
        "last_event_time": "2026-07-18 07:15:00",
    },
}


def get_lot_info(lot_id: str) -> dict:
    """Lot 1개의 현재 상태를 반환한다."""
    lot_id = lot_id.strip().upper()
    if not _LOT_PATTERN.match(lot_id):
        raise ToolError("조회 실패: Lot 번호 형식을 확인하세요 (예: LOT2401A001)")

    lot = _MOCK_LOTS.get(lot_id)
    if lot is None:
        raise ToolError(
            f"조회 실패: '{lot_id}' 에 해당하는 Lot 이 없습니다. 번호를 다시 확인하세요."
        )
    return lot


def get_lot_history(lot_id: str) -> list[dict]:
    """Lot 의 공정 이동 이력을 반환한다.

    TODO: 구현 (step 별 track-in/out 시각, 설비, 작업자)
    """
    raise ToolError("조회 실패: Lot 이력 조회는 아직 구현되지 않은 기능입니다.")
