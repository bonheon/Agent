"""Hold / 공정금지 조회 비즈니스 로직 — 스텁.

순수 파이썬 — 프레임워크 의존 없음.
"""
from core.errors import ToolError


def get_hold_list(target: str) -> list[dict]:
    """Lot 번호 또는 공정 step 기준으로 Hold/공정금지 내역을 반환한다.

    TODO: 구현 — target 이 Lot 번호 형식이면 해당 Lot 의 Hold 이력,
          step 코드 형식이면 해당 공정의 공정금지 목록을 조회.
    """
    raise ToolError("조회 실패: Hold/공정금지 조회는 아직 구현되지 않은 기능입니다.")
