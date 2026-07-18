"""설비(EQ) 관련 tool — core/eq_service 를 호출하는 얇은 wrapper. (스텁)"""
from langchain_core.tools import tool

from core import eq_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def get_eq_status(eq_id: str) -> str:
    """설비 1대의 현재 상태(RUN/IDLE/PM/DOWN)와 진행 중인 Lot 을 조회한다.

    언제 사용: 사용자가 특정 설비 호기를 언급하며 "지금 돌아가?", "왜 서 있어",
    "PM 중이야?" 등 설비의 현재 상태를 물을 때 사용한다.

    다른 tool 과의 구분:
    - 설비가 아니라 Lot 기준 위치/상태는 get_lot_info 를 사용한다.
    - 설비 알람의 조치 방법 등 문서 지식은 search_knowledge 를 사용한다.

    Args:
        eq_id: 설비 호기 ID (예: PHO-301).
    """
    # TODO: eq_service 구현 후 결과 포매팅 추가
    return str(eq_service.get_eq_status(eq_id))


register(get_eq_status)
