"""ceeria MCP 서버 — registry 에 등록된 tool 전부를 MCP tool 로 노출한다.

공용 tool(tools/*_tools.py)과 skill 전용 tool(skills/<name>/tools.py)을 가리지 않고
registry 에 있는 것을 그대로 내보낸다. tool 을 추가하면 이 파일은 고치지 않는다.
비즈니스 로직은 core/ 와 skills/*/services 에만 있으므로 여기서는 "MCP 로 어떻게
보이는가"만 감싼다 — 로직 중복이 없다.

Coris 허브(backend)는 이 서버를 mcp_servers.yaml 의 url 로 붙여 쓴다. 이 경로에서는
ceeria agent(ReAct 루프/프롬프트)를 거치지 않고 허브의 LLM 이 직접 tool 을 고르므로,
tool docstring 품질이 허브 쪽 tool 선택 정확도를 좌우한다.

tool 은 safe_tool 을 거치므로 ToolError 는 예외가 아니라 안내 문자열로 돌아간다
(LangGraph 경로와 같은 동작).

실행 (siria/ 루트에서):
    python -m adapters.mcp_server              # stdio — client 예제가 프로세스로 띄우는 방식
    python -m adapters.mcp_server --http       # http://127.0.0.1:8200/mcp — 허브 연결용
    CEERIA_MCP_PORT=8300 python -m adapters.mcp_server --http

직접 눈으로 확인하려면:
    mcp dev adapters/mcp_server.py             # 웹 inspector 로 tool 호출 테스트
    python -m adapters.mcp_client_example
"""
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from tools import registry

log = logging.getLogger("ceeria.mcp")

HOST = os.getenv("CEERIA_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("CEERIA_MCP_PORT", "8200"))
NAME = "ceeria"
INSTRUCTIONS = "반도체 라인 조회 · 판단 tool (Lot/설비/재공/Hold/Part/지식베이스/검사·MCRS)"


def build_server() -> FastMCP:
    server = FastMCP(NAME, instructions=INSTRUCTIONS, host=HOST, port=PORT, stateless_http=True)
    for t in registry.all_tools():
        # @tool 이 감싼 원래 함수 — 타입힌트가 그대로 MCP 입력 스키마가 된다.
        # 반환값은 이미 LLM 용 문자열이므로 structured output 으로 다시 감싸지 않는다.
        server.add_tool(t.func, name=t.name, description=t.description, structured_output=False)
    return server


mcp = build_server()  # `mcp dev adapters/mcp_server.py` 가 모듈 전역의 서버 객체를 찾는다


if __name__ == "__main__":
    if "--http" in sys.argv:
        logging.basicConfig(level=logging.INFO)
        log.info("ceeria MCP: http://%s:%d/mcp (%d tools)", HOST, PORT, len(registry.all_tools()))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio — stdout 은 프로토콜 전용이라 로그를 찍지 않는다
