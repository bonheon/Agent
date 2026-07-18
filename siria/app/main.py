"""FastAPI 진입점.

실행 (siria/ 루트에서):
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.factory import CONFIG_DIR, SiriaAgent, create_agent
from observability import setup_tracing
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
    """사용 가능한 agent 정의(yaml) 목록."""
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


@app.get("/tools")
def list_tools() -> dict[str, str]:
    """registry 에 등록된 전체 tool 목록 (이름: 설명 첫 줄)."""
    return registry.list_tools()
