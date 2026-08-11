"""MCP 서버 예제 — core/lot_service 를 MCP tool 로 노출한다.

핵심 아이디어: LangGraph tool(tools/lot_tools.py)과 똑같이 core/ 의 서비스
함수를 그대로 호출한다. 비즈니스 로직은 core/ 에만 있으므로 여기서는
"MCP 프로토콜로 어떻게 보이는가"만 감싼다 — 로직 중복이 없다.

가이아2.0 스킬카드 연동 시 이 서버가 호출 대상이 된다 (README '가이아2.0 연동
설계' 참고). 이 경로에서는 씨리아 agent(ReAct 루프/프롬프트)를 거치지 않고
가이아 LLM 이 직접 tool 을 선택하므로, 노출할 tool 의 docstring 품질이
가이아 쪽 tool 선택 정확도를 좌우한다.

실행:
    pip install "mcp[cli]"
    python -m adapters.mcp_server          # stdio 서버로 실행 (client 가 기동)

직접 눈으로 확인하려면:
    mcp dev adapters/mcp_server.py         # 웹 inspector 로 tool 호출 테스트
또는 client 예제를 실행:
    python -m adapters.mcp_client_example
"""
from mcp.server.fastmcp import FastMCP

from core import lot_service
from core.errors import ToolError

mcp = FastMCP("siria")


@mcp.tool()
def get_lot_info(lot_id: str) -> dict:
    """Lot 번호 1개의 현재 상태(공정 step, 진행 설비, 수량, Hold 여부)를 조회한다.

    Args:
        lot_id: Lot 번호 (예: LOT2401A001). 대소문자 무관.
    """
    try:
        return lot_service.get_lot_info(lot_id)
    except ToolError as e:
        # LangGraph tool 은 safe_tool 데코레이터가 문자열로 흡수하지만,
        # MCP 는 raise 된 예외를 그대로 client 에러로 전달한다.
        raise ValueError(str(e)) from e


if __name__ == "__main__":
    mcp.run()
