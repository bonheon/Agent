"""Tool 공통 유틸: 에러 처리.

원칙: raw exception/traceback 을 LLM 에 그대로 반환하지 않는다.
LLM 이 "다음에 뭘 해야 할지" 판단할 수 있는 한국어 안내 메시지로 변환한다.
"""
import functools
import logging

from core.errors import ToolError  # noqa: F401  (tool 모듈들이 여기서 import 해도 됨)

logger = logging.getLogger(__name__)


def safe_tool(func):
    """모든 tool 함수에 적용하는 에러 처리 데코레이터.

    - ToolError    → 메시지를 그대로 반환 (core 가 만든 안내 메시지)
    - 그 외 예외   → traceback 은 서버 로그에만 남기고,
                     LLM 에는 일반화된 한국어 안내 메시지를 반환

    주의: @tool 보다 안쪽(함수에 가까운 쪽)에 붙여야 type hint / docstring
    기반 스키마 자동 생성이 깨지지 않는다.

        @tool
        @safe_tool
        def get_lot_info(lot_id: str) -> str: ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            return str(e)
        except Exception:
            logger.exception("tool 실행 중 예상치 못한 에러: %s", func.__name__)
            return (
                f"조회 실패: '{func.__name__}' 실행 중 내부 오류가 발생했습니다. "
                "입력값 형식을 다시 확인해 보고, 문제가 반복되면 이 tool 재시도를 "
                "멈추고 사용자에게 시스템 오류가 발생했다고 알려주세요."
            )

    return wrapper
