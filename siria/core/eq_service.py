"""설비(EQ) 조회 비즈니스 로직 — 스텁.

순수 파이썬 — 프레임워크 의존 없음.
"""
from core.errors import ToolError


def get_eq_status(eq_id: str) -> dict:
    """설비 1대의 현재 상태(RUN/IDLE/PM/DOWN, 진행 중 Lot)를 반환한다.

    TODO: 구현 — eq_id 형식 검증 후 core/db.py 로 조회.
          형식 오류/미존재 시 ToolError 로 한국어 안내 메시지 반환.
    """
    raise ToolError("조회 실패: 설비 상태 조회는 아직 구현되지 않은 기능입니다.")
