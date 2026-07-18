"""재공(WIP) 관련 tool — core/wip_service 를 호출하는 얇은 wrapper. (스텁)"""
from langchain_core.tools import tool

from core import wip_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def get_wip_summary(area: str) -> str:
    """공정 area 기준 step 별 재공(WIP) Lot 수/수량 집계를 조회한다.

    언제 사용: "PHOTO 재공 얼마나 쌓였어", "ETCH 구간 물량 현황" 등
    여러 Lot 의 집계 현황을 물을 때 사용한다.

    다른 tool 과의 구분:
    - 특정 Lot 1개의 상태는 get_lot_info 를 사용한다. 이 tool 은 개별 Lot 이 아닌
      구간 단위 집계만 반환한다.

    Args:
        area: 공정 area 코드 (예: PHOTO, ETCH, DIFF, CVD).
    """
    # TODO: wip_service 구현 후 결과 포매팅 추가
    return str(wip_service.get_wip_summary(area))


register(get_wip_summary)
