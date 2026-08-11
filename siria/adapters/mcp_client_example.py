"""MCP 개념을 눈으로 확인하기 위한 client 예제.

MCP 는 client-server 프로토콜이다:
  - server(mcp_server.py) 가 tool 목록과 스키마를 노출한다.
  - client(이 파일) 가 프로세스로 server 를 띄우고, stdio 로 JSON-RPC 메시지를
    주고받으며 "어떤 tool 이 있는지 물어보기" → "tool 을 실제로 호출하기" 를
    수행한다.
  - LangGraph agent 안의 @tool 과 다른 점: LangGraph tool 은 같은 파이썬
    프로세스 안에서 함수를 직접 호출하지만, MCP tool 은 프로세스 경계를 넘어
    (여기서는 stdio, 원격이면 HTTP) 호출된다. 그래서 가이아2.0 같은 "다른
    회사 시스템"이 씨리아 코드를 import 하지 않고도 tool 을 쓸 수 있다.

실행 (siria/ 디렉토리에서):
    pip install "mcp[cli]"
    python -m adapters.mcp_client_example
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# server 를 별도 프로세스로 띄우기 위한 실행 파라미터.
# "python -m adapters.mcp_server" 를 그대로 서브프로세스로 실행한다.
# sys.executable 을 써서 지금 이 스크립트를 실행 중인 것과 같은 인터프리터
# (venv 등)로 서버를 띄운다.
server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "adapters.mcp_server"],
)


async def main() -> None:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. server 가 어떤 tool 을 노출하는지 물어본다.
            #    (docstring 이 description 으로, type hint 가 JSON 스키마로 자동 변환됨)
            tools = await session.list_tools()
            print("=== 노출된 tool 목록 ===")
            for t in tools.tools:
                print(f"- {t.name}: {t.description.strip().splitlines()[0]}")

            # 2. 정상 케이스: 존재하는 lot 조회
            print("\n=== get_lot_info('LOT2401A001') ===")
            result = await session.call_tool(
                "get_lot_info", {"lot_id": "LOT2401A001"}
            )
            for block in result.content:
                print(block.text)

            # 3. 에러 케이스: 존재하지 않는 lot 조회
            #    core.errors.ToolError 가 mcp_server.py 에서 ValueError 로
            #    변환되어 client 쪽에 isError=True 로 전달되는 걸 확인한다.
            print("\n=== get_lot_info('LOT9999Z999') (에러 케이스) ===")
            result = await session.call_tool(
                "get_lot_info", {"lot_id": "LOT9999Z999"}
            )
            print("isError:", result.isError)
            for block in result.content:
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
