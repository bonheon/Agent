"""
로컬 MCP 서버 — 회사 MCP 서버 대역.

tools/langgraph_tools.py 의 tool 을 그대로 MCP(streamable HTTP)로 노출한다.
백엔드는 이 서버를 회사 MCP 서버와 똑같은 방식(mcp_servers.yaml 의 url)으로 붙으므로,
회사에서는 이 프로세스를 띄우지 않고 yaml 의 url 만 회사 주소로 바꾸면 된다.

실행 (backend/ 에서):
    python -m mcp_server.fab_tools              # http://localhost:8100/mcp
    MCP_PORT=8200 python -m mcp_server.fab_tools
"""
import logging
import os

from tools.langgraph_tools import TOOLS

try:  # mcp 1.x (현재 langchain-mcp-adapters 가 지원하는 버전)
    from mcp.server.fastmcp import FastMCP
    MCP_V2 = False
except ModuleNotFoundError:  # mcp 2.x — FastMCP 가 MCPServer 로 이름이 바뀜
    from mcp.server.mcpserver import MCPServer
    MCP_V2 = True

log = logging.getLogger("mcp_server")

HOST = os.getenv("MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_PORT", "8100"))
NAME, INSTRUCTIONS = "fab-tools", "반도체 Fab 라인 조회 tool (Mock 데이터)"


def build_server():
    if MCP_V2:
        server = MCPServer(name=NAME, instructions=INSTRUCTIONS)
    else:  # 1.x 는 host/port 를 생성자에서 받는다
        server = FastMCP(NAME, instructions=INSTRUCTIONS, host=HOST, port=PORT, stateless_http=True)
    for t in TOOLS:
        # @tool 이 감싼 원래 함수 — 타입힌트(Literal 등)가 그대로 MCP 입력 스키마가 된다.
        # 반환값은 이미 JSON 문자열이므로 structured output 으로 다시 감싸지 않는다.
        server.add_tool(t.func, name=t.name, description=t.description, structured_output=False)
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    srv = build_server()
    log.info("fab-tools MCP: http://%s:%d/mcp (%d tools)", HOST, PORT, len(TOOLS))
    if MCP_V2:
        import anyio
        anyio.run(lambda: srv.run_streamable_http_async(host=HOST, port=PORT, stateless_http=True))
    else:
        srv.run(transport="streamable-http")
