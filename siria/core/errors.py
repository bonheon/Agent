"""core 공통 예외.

core/ 는 프레임워크(LangChain 등) 의존이 없어야 하므로 예외 정의도 여기에 둔다.
tools/common.py 가 이걸 import 해서 LLM 응답 메시지로 변환한다.
"""


class ToolError(Exception):
    """LLM(또는 사용자)에게 그대로 보여줄 한국어 안내 메시지를 담는 예외.

    raw traceback 대신 "다음에 뭘 해야 할지" 판단 가능한 메시지를 담는다.

    사용 예:
        raise ToolError("조회 실패: Lot 번호 형식을 확인하세요 (예: LOT2401A001)")
    """
