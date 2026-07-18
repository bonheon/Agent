"""Part(설비 부품) 재고 조회 비즈니스 로직 — 스텁.

순수 파이썬 — 프레임워크 의존 없음.
"""
from core.errors import ToolError


def get_part_inventory(part_no: str) -> dict:
    """Part 번호로 현재 재고 수량/위치/입고 예정을 반환한다.

    TODO: 구현 — part_no 형식 검증 후 core/db.py 로 조회.
    """
    raise ToolError("조회 실패: Part 재고 조회는 아직 구현되지 않은 기능입니다.")
