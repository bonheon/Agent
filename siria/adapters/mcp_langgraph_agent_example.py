""""다른 LangGraph agent" 가 씨리아의 MCP tool 을 붙여 쓰는 예제.

앞서 만든 mcp_client_example.py 는 MCP 프로토콜 자체(list_tools/call_tool)를
직접 다뤘다. 이 파일은 한 단계 위 — **씨리아 코드를 import 하지 않는 별도의
LangGraph agent** 가 langchain-mcp-adapters 로 MCP tool 을 평범한
LangChain BaseTool 처럼 받아서 자기 agent 에 꽂아 넣는 흐름을 보여준다.

핵심 포인트: MultiServerMCPClient.get_tools() 가 돌려주는 tool 은
tools/registry.py 의 get_tools([...]) 가 돌려주는 tool 과 타입이 완전히
같다(langchain_core.tools.BaseTool). 그래서 agents/factory.py 의
create_react_agent(llm, tools=..., prompt=...) 호출부에 그대로 넣을 수 있다
— 다른 점은 tool 의 출처가 로컬 import 가 아니라 MCP 서버라는 것뿐이다.

실행:
    pip install "mcp[cli]" langchain-mcp-adapters langgraph langchain-openai
    python -m adapters.mcp_langgraph_agent_example

LLM 엔드포인트(SIRIA_LLM_BASE_URL 등)가 아직 설정 전이어도, tool 로딩과
직접 호출까지는 LLM 없이 확인 가능하다. agent 를 실제로 굴려보려면
config.py 의 TODO(내부망 LLM)를 먼저 채워야 한다.
"""
import asyncio
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

# 이 dict 가 "등록"에 해당하는 부분이다 — 어떤 이름으로, 어떻게 접속할지만
# 적는다. 지금은 로컬 stdio 로 서버 프로세스를 직접 띄우지만, 원격 서버라면
# {"transport": "streamable_http", "url": "https://.../mcp"} 로 바뀔 뿐
# 이후 코드는 동일하다.
MCP_SERVERS = {
    "siria": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "adapters.mcp_server"],
    },
}


async def main() -> None:
    client = MultiServerMCPClient(MCP_SERVERS)

    # 1. MCP 서버(들)에서 tool 을 끌어와 BaseTool 리스트로 변환한다.
    #    tools/registry.py 의 get_tools(["get_lot_info"]) 와 결과 타입이 동일하다.
    tools = await client.get_tools()
    print("=== langchain-mcp-adapters 가 변환한 tool ===")
    for t in tools:
        print(f"- {t.name} ({type(t).__name__}): {t.description.strip().splitlines()[0]}")

    # 2. LLM 없이 tool 자체가 정상 동작하는지 직접 호출해서 확인.
    #    (agent 에 넣기 전 단독 동작을 검증하는 습관 — LLM 호출 비용/설정 없이도 가능)
    lot_tool = next(t for t in tools if t.name == "get_lot_info")
    print("\n=== tool.ainvoke({'lot_id': 'LOT2401A001'}) 직접 호출 ===")
    result = await lot_tool.ainvoke({"lot_id": "LOT2401A001"})
    print(result)

    # 3. 실제 agent 에 꽂아 넣는 방법 — agents/factory.py 의 create_agent() 와
    #    같은 모양이다. 다만 tools 출처가 tools/registry.py 가 아니라
    #    MCP client 라는 점만 다르다.
    print("\n=== agent 에 연결하는 방법 (LLM 엔드포인트 필요) ===")
    try:
        from config import get_llm, settings
        from langgraph.prebuilt import create_react_agent

        if not settings.llm_base_url:
            print("SIRIA_LLM_BASE_URL 미설정 — agent 실행은 건너뜀 (tool 연동 자체는 위에서 확인됨).")
            return

        agent = create_react_agent(get_llm(), tools=tools, prompt="당신은 반도체 라인 조회 assistant 입니다.")
        result = await agent.ainvoke({"messages": [("user", "LOT2401A001 지금 상태 알려줘")]})
        print(result["messages"][-1].content)
    except Exception as e:  # noqa: BLE001 — 예제 스크립트: 설정 미비 시 원인만 보여주고 종료
        print(f"agent 실행 생략 (원인: {e})")


if __name__ == "__main__":
    asyncio.run(main())
