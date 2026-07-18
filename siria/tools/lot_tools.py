"""Lot 관련 tool — core/lot_service 를 호출하는 얇은 wrapper.

이 파일에는 비즈니스 로직(쿼리, 검증, mock 데이터)이 없어야 한다.
스키마는 @tool + type hint + docstring 으로 자동 생성된다 (수작업 JSON 금지).
"""
from langchain_core.tools import tool

from core import lot_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def get_lot_info(lot_id: str) -> str:
    """Lot 번호 1개의 현재 상태(현재 공정 step, 진행 설비, 수량, Hold 여부)를 조회한다.

    언제 사용: 사용자가 특정 Lot 번호를 언급하며 "어디 있어", "상태 알려줘",
    "몇 매야", "Hold 걸렸어?" 등 단일 Lot 의 현재 상황을 물을 때 사용한다.

    다른 tool 과의 구분:
    - 여러 Lot 의 공정 구간별 집계(재공 수량)는 get_wip_summary 를 사용한다.
    - Hold 의 상세 사유/이력이나 공정금지 내역은 get_hold_list 를 사용한다.
      (이 tool 은 Hold 여부와 대표 사유 한 줄만 보여준다)
    - Lot 이 지나온 공정 이력은 get_lot_history 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: LOT2401A001). 대소문자 무관.
    """
    info = lot_service.get_lot_info(lot_id)
    lines = [
        f"Lot: {info['lot_id']} ({info['product']})",
        f"현재 공정: {info['step']} ({info['step_desc']})",
        f"진행 설비: {info['eq_id'] or '미할당 (대기 중)'}",
        f"수량: {info['qty']}매",
        f"상태: {info['status']}",
        f"최종 이벤트: {info['last_event_time']}",
    ]
    if info["hold"]:
        lines.append(f"Hold 사유: {info['hold_reason']}")
    return "\n".join(lines)


@tool
@safe_tool
def get_lot_history(lot_id: str) -> str:
    """Lot 이 지나온 공정 이동 이력(step 별 track-in/out 시각, 설비)을 조회한다.

    언제 사용: "이 Lot 어제 어디 지나갔어", "PHOTO 공정 언제 통과했어" 등
    과거 이력을 물을 때 사용한다.

    다른 tool 과의 구분:
    - 현재 위치/상태만 필요하면 get_lot_info 를 사용한다 (이 tool 보다 가볍다).

    Args:
        lot_id: Lot 번호 (예: LOT2401A001). 대소문자 무관.
    """
    history = lot_service.get_lot_history(lot_id)
    return "\n".join(str(h) for h in history)


register(get_lot_info)
register(get_lot_history)
