"""
LangGraph 에이전트 실행부 — chat(스트리밍)과 이벤터(일괄 실행)가 함께 쓴다.

어떤 agent 와 tool 로 실행할지는 hub.routing 이 정하고(Plan), 여기서는 그대로 실행만 한다.
tool 부분집합마다 그래프를 따로 컴파일해 캐시한다.
LLM 이 보는 tool 목록 자체를 줄여야 선택 정확도가 오르기 때문에,
프롬프트로 "이 tool 만 써라" 라고 하는 대신 bind_tools 대상을 바꾼다.
"""
import os
import time
from collections import OrderedDict
from typing import AsyncGenerator, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from hub.catalog import AGENTS_BY_ID, TOOLS_BY_NAME
from hub import catalog, routing, store
from hub.routing import Plan

MODEL = "gpt-4o"
RECURSION_LIMIT = 16

SYSTEM_PROMPT = """당신은 반도체 제조 공정 전문 AI 어시스턴트입니다.
사용자의 질문에 맞는 도구를 사용해 데이터를 조회하고, 명확하고 전문적인 답변을 제공합니다.

[차트 태그 — 반드시 응답에 포함하여 시각화]
- Wafer Map:             [WAFER_MAP:{lot_id}]
- 트렌드 차트:           [TREND_CHART:{lot_id}:{metric}]
- Defect Map:            [DEFECT_MAP:{lot_id}:{wafer_no}]
- Defect 트렌드:         [DEFECT_TREND:{lot_id}:{defect_type}]
- 수율+Chip Kill:        [YIELD_DEFECT:{lot_id}:{wafer_no}]
- Defect-수율 이력 분석: [DEFECT_YIELD_HISTORY:{lot_id}:{defect_type}]
- Lot 수율 Grouping 분석: [YIELD_ANALYSIS:{lot_ids_콤마구분}:{group_by}:{params_콤마구분}]
  예) [YIELD_ANALYSIS:TE2FE35,TE2FE36,TE2FE37:recipe:PT1H,PT1H_outer,bl_lkg,ledic]
- Step 간 Defect Overlay: [DEFECT_STEP_OVERLAY:{lot_id}:{wafer_no}]
  예) [DEFECT_STEP_OVERLAY:TE2FE35:5]  ← 이전 step들과 현재 step defect을 한 wafer에 overlay
- 전일 이슈 리포트:   [DAILY_REPORT:{area_key}]
  예) [DAILY_REPORT:M14 CMP]  ← WIP·Hold·Defect·장비Down 교차 분석 + 우선 대응 액션
- WIP 현황 대시보드: [WIP_STATUS:{area_key}]
  예) [WIP_STATUS:M14 CMP]  ← 공정 그룹별 WIP + 장비 status + move 실적/목표/예상

[기능 독립 호출 원칙]
- 사용자가 요청하는 기능은 순서 없이 즉시 실행하세요.
- Defect Map → Trend → 수율 분석은 권장 순서이지, 강제 순서가 아닙니다.
- 사용자가 "BRIDGE trend 보여줘", "수율 바로 분석해줘" 처럼 직접 요청하면 즉시 실행하세요.

[각 기능 안내]
Defect Map 조회 후:
  - 유형별 건수 요약 후 자연스럽게 "Trend나 수율 이력 분석도 확인하시겠어요?" 제안 가능 (강제 아님)

트렌드 조회 후:
  - OOC 슬롯이 있으면 표로 정리
  - "해당 OOC Slot들의 Wafer Map도 확인하시겠어요?" 제안 가능 (강제 아님)

Defect-수율 이력 분석 (get_defect_yield_history):
  - 현재 wafer의 수율이 아직 없을 때, 같은 lot의 다른 슬롯 이력을 기반으로 chip kill 가능성 추정
  - 상관계수와 슬롯별 defect 건수 vs 수율 scatter, 평균 kill rate 제공
  - [DEFECT_YIELD_HISTORY:{lot_id}:{defect_type}] 태그 포함

단일 Wafer 수율 분석 (get_yield_defect):
  - 특정 wafer의 bin 데이터와 defect 위치 오버레이
  - [YIELD_DEFECT:{lot_id}:{wafer_no}] 태그 포함

Lot Grouping 수율 분석 (analyze_yield_grouping):
  - 사용 가능 Lot: TE2FE35, TE2FE36, TE2FE37, TE2FE38, TE2FE39, TE2FE40, TE2FE41, TE2FE42
  - Grouping 기준: recipe(공정 레시피), equipment(장비), process_id(공정 ID), custom_group(사용자 정의)
  - Pass rate 파라미터: PT1H, PT1H_outer, PT1H_center, PT1H_inner
  - Fail rate 파라미터: bl_lkg, ledic (나중에 추가 예정)
  - 사용자가 Lot을 명시하지 않으면 전체 Lot을 포함하거나, 어떤 Lot을 비교할지 자연스럽게 물어보세요.
  - 분석 후 반드시 [YIELD_ANALYSIS:...] 태그를 포함하세요.
  - Excel 다운로드 버튼은 차트 카드에 자동으로 포함됩니다.

전일 이슈 리포트 (get_daily_report):
  - WIP 변동(시작→종료), 이동 달성률, 신규 Hold 건수/원인/공정별 분류
  - Defect 스파이크 장비 식별 (기준 대비 +% 초과)
  - 장비 DOWN 이력 + 현재 DOWN 중인 장비 + 대기 WIP 건수
  - 교차 분석: DOWN 장비 + 대기 WIP + Defect 연관 → 우선 복구 순위
  - 오늘 우선 대응 액션 리스트 (P1 긴급 / P2 주의 / P3 관찰)
  - [DAILY_REPORT:{area_key}] 태그 포함
  - '전일 이슈', '아침 보고', '어제 이슈' 등의 요청에 사용

WIP 현황 조회 (get_wip_status):
  - 지원 Area: 'M14 CMP' (STI·Poly·W·Cu CMP), 'M14 Photo' (DUV·EUV·Coat/Dev)
  - 공정 그룹별: WIP 재공량(Running/Queue), 장비 Status, 금일 이동 실적/목표, EOD 예상 이동량
  - 장비 Status: RUNNING(가동), IDLE(대기), DOWN(고장), PM(예방정비), SETUP(셋업)
  - [WIP_STATUS:{area_key}] 태그 포함

Step 간 Defect Overlay 분석 (get_defect_step_overlay):
  - 이전 step(LITHO-01, ETCH-01, CMP-01)과 현재 step(INSP-01)의 defect을 동일 wafer에 overlay
  - carryover defect: 동일 위치 근방에 복수 step에서 발생한 defect — step별로 유형이 다를 수 있음
  - 예: LITHO의 PARTICLE → ETCH의 PIT → INSP의 CLUSTER (공정을 거치며 형태 변형)
  - [DEFECT_STEP_OVERLAY:{lot_id}:{wafer_no}] 태그 포함

항상 한국어로 응답"""


def build_prompt(plan: Plan, skill: Optional[dict], user_memory: str = "") -> str:
    agent = AGENTS_BY_ID[plan.agent_id]
    prompt = SYSTEM_PROMPT + f"\n\n[에이전트: {agent['name']}]\n{agent['prompt'].strip()}"
    if skill:
        prompt += (
            f"\n\n[스킬: {skill['name']}]\n{skill['description']}\n"
            f"아래 절차를 따르세요. 사용자가 특정 데이터 하나만 요청하면 해당 tool 만 호출하고 끝냅니다.\n"
            f"{skill['instructions']}"
        )
    prompt += user_memory  # hub.memory.for_prompt() 결과 — 없으면 빈 문자열
    if plan.unavailable:
        # 빠진 tool 을 알리지 않으면 LLM 이 데이터 없이 답을 지어낸다
        prompt += (
            f"\n\n[사용 불가 tool] {', '.join(plan.unavailable)} — 지금 응답하지 않는 tool 입니다. "
            f"이 데이터가 필요한 질문이면 조회할 수 없다고 분명히 알리고 추정으로 채우지 마세요."
        )
    return prompt


def _build_graph(tools: list):
    llm = ChatOpenAI(model=MODEL, api_key=os.getenv("OPENAI_API_KEY"), streaming=True)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    # config 를 반드시 전달해야 astream_events 가 on_chat_model_stream 을 잡는다
    def agent_node(state: MessagesState, config: RunnableConfig):
        return {"messages": [llm_with_tools.invoke(state["messages"], config)]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
    return graph.compile()


# lazy — main.py 의 load_dotenv() 이후 첫 요청 시점에 만든다
# 사용자가 tool 을 자유롭게 조합하므로 조합 수가 계속 늘 수 있다 — LRU 로 상한
GRAPH_CACHE_MAX = 32
_graphs: "OrderedDict[tuple[str, ...], object]" = OrderedDict()
_graphs_version = 0


def _get_graph(tool_names: list[str]):
    global _graphs_version
    if _graphs_version != catalog.VERSION:  # MCP 를 다시 받아왔으면 낡은 tool 객체를 쥔 그래프는 버린다
        _graphs.clear()
        _graphs_version = catalog.VERSION
    key = tuple(sorted(tool_names))
    if key in _graphs:
        _graphs.move_to_end(key)
    else:
        _graphs[key] = _build_graph([TOOLS_BY_NAME[n] for n in key])
        if len(_graphs) > GRAPH_CACHE_MAX:
            _graphs.popitem(last=False)
    return _graphs[key]


def to_lc_messages(system_prompt: str, messages: list[dict]) -> list:
    lc: list = [SystemMessage(content=system_prompt)]
    for m in messages:
        if m["role"] == "user":
            lc.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant" and m["content"]:
            lc.append(AIMessage(content=m["content"]))
    return lc


async def stream(messages: list[dict], plan: Plan, skill: Optional[dict],
                 user_memory: str = "") -> AsyncGenerator[dict, None]:
    """에이전트 실행 이벤트를 순서대로 yield. plan 은 hub.routing.resolve() 결과.

    {"type": "delta", "text": ...}
    {"type": "tool_start", "id", "name", "args"}
    {"type": "tool_end", "id", "name", "ms", "ok"}
    """
    graph = _get_graph(plan.tools)
    started: dict[str, float] = {}

    async for ev in graph.astream_events(
        {"messages": to_lc_messages(build_prompt(plan, skill, user_memory), messages)},
        {"recursion_limit": RECURSION_LIMIT},
        version="v2",
    ):
        kind = ev["event"]
        if kind == "on_chat_model_stream":
            chunk = ev["data"]["chunk"]
            if chunk.content:
                yield {"type": "delta", "text": chunk.content}
        elif kind == "on_tool_start":
            started[ev["run_id"]] = time.perf_counter()
            args = ev["data"].get("input") or {}
            yield {"type": "tool_start", "id": ev["run_id"], "name": ev["name"],
                   "args": args if isinstance(args, dict) else {"input": str(args)}}
        elif kind in ("on_tool_end", "on_tool_error"):
            t0 = started.pop(ev["run_id"], time.perf_counter())
            yield {"type": "tool_end", "id": ev["run_id"], "name": ev["name"],
                   "ms": round((time.perf_counter() - t0) * 1000), "ok": kind == "on_tool_end"}


async def run(messages: list[dict], agent_id: Optional[str], skill_id: Optional[str]) -> tuple[str, list[dict], Plan]:
    """스트리밍 없이 끝까지 실행 — (최종 텍스트, tool 실행 기록, 실행 계획)."""
    skill = store.get_item("skills", skill_id) if skill_id else None
    plan = await routing.resolve(messages, agent_id, skill, None, None)
    text: list[str] = []
    runs: dict[str, dict] = {}
    async for ev in stream(messages, plan, skill):
        if ev["type"] == "delta":
            text.append(ev["text"])
        elif ev["type"] == "tool_start":
            runs[ev["id"]] = {"name": ev["name"], "args": ev["args"], "ms": None, "ok": None}
        elif ev["type"] == "tool_end" and ev["id"] in runs:
            runs[ev["id"]].update(ms=ev["ms"], ok=ev["ok"])
    return "".join(text), list(runs.values()), plan
