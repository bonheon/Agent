"""Part 재고 관련 tool — core/part_service 를 호출하는 얇은 wrapper. (스텁)"""
from langchain_core.tools import tool

from core import part_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def get_part_inventory(part_no: str) -> str:
    """설비 부품(Part) 번호로 현재 재고 수량, 보관 위치, 입고 예정을 조회한다.

    언제 사용: "OO 부품 재고 있어?", "이 파트 언제 입고돼" 등 설비 유지보수용
    부품 재고를 물을 때 사용한다.

    다른 tool 과의 구분:
    - 생산 물량(웨이퍼/Lot)은 get_lot_info / get_wip_summary 를 사용한다.
      이 tool 은 설비 부품 재고 전용이다.

    Args:
        part_no: Part 번호 (예: P-88231).
    """
    # TODO: part_service 구현 후 결과 포매팅 추가
    return str(part_service.get_part_inventory(part_no))


register(get_part_inventory)
