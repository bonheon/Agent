"""FastAPI 진입점.

실행 (siria/ 루트에서):
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.factory import SiriaAgent, agent_config_paths, create_agent
from observability import setup_tracing
from skills import loader as skill_loader
from tools import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    yield


app = FastAPI(title="Siria — Fab Line LLM Agent", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    agent: str = "line_agent"


class ChatResponse(BaseModel):
    agent: str
    answer: str


@lru_cache
def _get_agent(name: str) -> SiriaAgent:
    """agent 는 정의가 바뀌지 않는 한 재사용한다 (요청마다 재생성하지 않음)."""
    return create_agent(name)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        agent = _get_agent(req.agent)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = agent.invoke(req.message)
    return ChatResponse(agent=req.agent, answer=result["messages"][-1].content)


@app.get("/agents")
def list_agents() -> list[str]:
    """사용 가능한 agent 정의 목록 (agents/configs + skill 내장 설정)."""
    return sorted(agent_config_paths())


@app.get("/tools")
def list_tools() -> dict[str, str]:
    """registry 에 등록된 전체 tool 목록 (이름: 설명 첫 줄)."""
    return registry.list_tools()


@app.get("/skills")
def list_skills() -> list[dict]:
    """정의된 skill 목록 (이름/설명/사용 tool).

    외부 플랫폼(가이아2.0 등)에 skill 을 등록할 때 필요한 메타데이터다.
    절차 본문은 용량이 크므로 여기서는 제외하고 /skills/{name} 으로 받는다.
    """
    return [
        {"name": s.name, "description": s.description, "tools": s.tools}
        for s in (skill_loader.load_skill(n) for n in skill_loader.list_skills())
    ]


@app.get("/skills/{name}")
def get_skill(name: str) -> dict:
    """skill 1개의 전체 정의 (절차 본문 포함)."""
    try:
        skill = skill_loader.load_skill(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "name": skill.name,
        "description": skill.description,
        "tools": skill.tools,
        "system_prompt": skill.system_prompt,
    }
