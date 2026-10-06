"""
분기점(agent 선택) + 최종 tool 계산.

1) candidates(): 사용자가 고른 tool · skill 필수 tool 을 모두 쓸 수 있는 agent 만 후보로 남긴다.
   → Router 가 사용자 선택과 어긋난 agent 를 고를 수 없다.
2) route(): 후보가 여럿일 때만 LLM 한 번. 직전 agent 를 유지하는 쪽으로 기울인다(sticky).
3) plan_tools(): 최종 tool 을 규칙으로 계산 — LLM 이 아니라 코드가 정한다.

     기본   = 사용자가 고른 group·tool  (없으면 skill tool, 그것도 없으면 agent 기본 group)
     최종   = (기본 ∪ skill 필수 tool) − 사용자가 끈 tool(필수 tool 제외)
              ∩ agent 허용 범위 ∩ 현재 사용 가능한 tool
   빠진 tool 은 이유와 함께 dropped 로 돌려준다 (route 이벤트 · 프롬프트에 노출).
"""
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from hub import catalog

log = logging.getLogger("routing")

ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")
MAX_TOOLS = 15          # 이 이상이면 선택 정확도가 눈에 띄게 떨어진다 — 경고만
ROUTER_HISTORY = 6      # Router 에 보여줄 최근 메시지 수
ROUTER_MSG_CHARS = 400  # 메시지당 길이 제한 (차트 태그 · 표가 긴 답변 대비)


class ToolSelection(BaseModel):
    groups: list[str] = []
    tools: list[str] = []
    exclude: list[str] = []


@dataclass
class Plan:
    agent_id: str
    route_mode: str                      # manual | single | sticky | router | fallback
    route_reason: str
    tools: list[str]
    locked: list[str]                    # skill 필수 tool — 끌 수 없음
    dropped: list[dict] = field(default_factory=list)   # {name, reason}
    warnings: list[str] = field(default_factory=list)

    @property
    def unavailable(self) -> list[str]:
        return [d["name"] for d in self.dropped if d["reason"] == "unavailable"]

    def summary(self) -> dict:
        agent = catalog.AGENTS_BY_ID[self.agent_id]
        return {"agent_name": agent["name"]} | asdict(self)

    def event(self) -> dict:
        return {"type": "route"} | self.summary()


# ── 선택 해석 ──────────────────────────────────────────────────

def _expand(sel: ToolSelection, warnings: list[str]) -> list[str]:
    unknown_g = [g for g in sel.groups if g not in catalog.GROUPS_BY_ID]
    if unknown_g:
        warnings.append(f"알 수 없는 group 무시: {', '.join(unknown_g)}")
    picked = catalog.group_tools(g for g in sel.groups if g in catalog.GROUPS_BY_ID)
    return list(dict.fromkeys(picked + sel.tools))


def skill_tools(skill: Optional[dict]) -> list[str]:
    return list(skill["tools"]) if skill and skill.get("tools") else []


def candidates(sel: ToolSelection, skill: Optional[dict]) -> list[str]:
    """요청된 tool(사용자 선택 + skill 필수)을 모두 허용하는 agent. 하나도 없으면 fallback 하나."""
    need = set(_expand(sel, [])) | set(skill_tools(skill))
    ok = [a["id"] for a in catalog.AGENTS if need <= set(catalog.agent_pool(a["id"]))]
    return ok or [catalog.FALLBACK_AGENT]


def plan_tools(agent_id: str, sel: ToolSelection, skill: Optional[dict],
               route_mode: str = "manual", route_reason: str = "") -> Plan:
    warnings: list[str] = []
    locked = skill_tools(skill)
    picked = _expand(sel, warnings)

    base = picked or locked or catalog.agent_defaults(agent_id)
    wanted = list(dict.fromkeys(base + locked))

    blocked = [n for n in sel.exclude if n in locked]
    if blocked:
        warnings.append(f"skill 필수 tool 은 끌 수 없음: {', '.join(blocked)}")
    excluded = set(sel.exclude) - set(locked)
    pool = set(catalog.agent_pool(agent_id))

    tools, dropped = [], []
    for name in wanted:
        if name in excluded:
            dropped.append({"name": name, "reason": "excluded"})
        elif name not in catalog.TOOLS_BY_NAME:
            dropped.append({"name": name, "reason": "unavailable"})
        elif name not in pool:
            dropped.append({"name": name, "reason": "not_allowed"})
        else:
            tools.append(name)

    outside = [d["name"] for d in dropped if d["reason"] == "not_allowed" and d["name"] in picked]
    if outside:
        warnings.append(f"선택한 tool 중 이 agent 허용 범위 밖이라 제외됨: {', '.join(outside)}")
    if not tools:
        warnings.append("켜진 tool 이 없어 조회 없이 답변합니다")
    if any(d["name"] in locked and d["reason"] != "excluded" for d in dropped):
        warnings.append("skill 필수 tool 일부를 쓸 수 없어 절차가 끝까지 진행되지 않을 수 있음")
    if len(tools) > MAX_TOOLS:
        warnings.append(f"tool {len(tools)}개 — {MAX_TOOLS}개를 넘으면 선택 정확도가 떨어집니다")
    return Plan(agent_id, route_mode, route_reason, tools, locked, dropped, warnings)


# ── Router (분기점) ────────────────────────────────────────────

class _Choice(BaseModel):
    agent_id: str = Field(description="선택한 agent id")
    reason: str = Field(description="한 문장 근거")


_router_llm = None


def _llm():
    global _router_llm  # lazy — load_dotenv() 이후에 만든다
    if _router_llm is None:
        _router_llm = ChatOpenAI(model=ROUTER_MODEL, temperature=0, api_key=os.getenv("OPENAI_API_KEY")) \
            .with_structured_output(_Choice)
    return _router_llm


def _router_prompt(cands: list[str], prev: Optional[str], skill: Optional[dict]) -> str:
    cards = "\n\n".join(
        f"- id: {a['id']} ({a['name']})\n  {a['route_hint'].strip()}"
        for a in catalog.AGENTS if a["id"] in cands
    )
    lines = [
        "사용자의 마지막 질문을 처리할 agent 하나를 고르세요. 아래 후보 id 중 하나만 답합니다.",
        "", cards, "",
    ]
    if prev in cands:
        lines.append(
            f"직전 턴은 '{prev}' 가 처리했습니다. 후속 질문(지시어, 같은 Lot/장비, '그거', '더 보여줘' 등)이면 "
            f"반드시 '{prev}' 를 유지하고, 주제가 분명히 바뀐 경우에만 바꾸세요."
        )
    if skill:
        lines.append(f"사용자가 선택한 skill: {skill['name']} — {skill.get('description', '')}")
    return "\n".join(lines)


def _history(messages: list[dict]) -> str:
    recent = [m for m in messages if m.get("content")][-ROUTER_HISTORY:]
    return "\n".join(f"[{m['role']}] {m['content'][:ROUTER_MSG_CHARS]}" for m in recent)


async def route(messages: list[dict], prev: Optional[str], cands: list[str],
                skill: Optional[dict]) -> tuple[str, str, str]:
    """(agent_id, mode, reason)"""
    if len(cands) == 1:
        return cands[0], "single", "선택한 tool/skill 을 처리할 수 있는 agent 가 하나뿐"
    fallback = prev if prev in cands else (catalog.FALLBACK_AGENT if catalog.FALLBACK_AGENT in cands else cands[0])
    try:
        choice: _Choice = await _llm().ainvoke([
            SystemMessage(content=_router_prompt(cands, prev, skill)),
            HumanMessage(content=_history(messages)),
        ])
    except Exception:  # noqa: BLE001 — 분기 실패로 대화가 막히면 안 된다
        log.exception("router failed")
        return fallback, "fallback", "Router 오류 — 기본 agent 로 처리"
    if choice.agent_id not in cands:
        return fallback, "fallback", f"Router 가 후보 밖 '{choice.agent_id}' 를 골라 기본 agent 로 처리"
    return choice.agent_id, ("sticky" if choice.agent_id == prev else "router"), choice.reason


async def resolve(messages: list[dict], agent_id: Optional[str], skill: Optional[dict],
                  sel: Optional[ToolSelection], prev_agent: Optional[str]) -> Plan:
    sel = sel or ToolSelection()
    if agent_id in catalog.AGENTS_BY_ID:
        return plan_tools(agent_id, sel, skill, "manual", "사용자가 agent 를 지정")
    # auto, 또는 옛 agent id(line/defect/yield 등) — 자동 분기로 처리
    chosen, mode, reason = await route(messages, prev_agent, candidates(sel, skill), skill)
    return plan_tools(chosen, sel, skill, mode, reason)
