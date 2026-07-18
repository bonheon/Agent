"""Hold/공정금지 관련 tool — core/hold_service 를 호출하는 얇은 wrapper. (스텁)"""
from langchain_core.tools import tool

from core import hold_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def get_hold_list(target: str) -> str:
    """Lot 번호 또는 공정 step 기준으로 Hold/공정금지 내역(사유, 등록 부서, 시각)을 조회한다.

    언제 사용: "이 Lot 왜 Hold 됐어", "ETCH-4100 공정금지 걸린 거 있어" 등
    Hold 의 상세 사유·이력이나 공정 단위 금지 내역을 물을 때 사용한다.

    다른 tool 과의 구분:
    - Lot 의 Hold '여부'만 필요하면 get_lot_info 로 충분하다. 이 tool 은
      사유/등록자/이력까지 필요한 경우에 사용한다.
    - Hold 해제 '절차' 같은 문서 지식은 search_knowledge 를 사용한다.

    Args:
        target: Lot 번호(예: LOT2401A001) 또는 공정 step 코드(예: ETCH-4100).
    """
    # TODO: hold_service 구현 후 결과 포매팅 추가
    return str(hold_service.get_hold_list(target))


register(get_hold_list)
