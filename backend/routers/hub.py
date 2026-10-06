from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import user_store
from hub import catalog, memory, routing, service, skills, store
from hub.users import current_user

router = APIRouter(prefix="/api/hub", tags=["hub"])


def _or_404(item: Optional[dict], what: str) -> dict:
    if item is None:
        raise HTTPException(404, f"{what} not found")
    return item


# ── 메타 / 대시보드 ───────────────────────────────────────────

@router.get("/meta")
async def get_meta():
    return await catalog.meta()


@router.post("/catalog/refresh")
async def refresh_catalog():
    """MCP 서버에서 tool 목록을 지금 다시 받아온다."""
    return await catalog.refresh()


class ResolveIn(BaseModel):
    agent_id: str
    skill_id: Optional[str] = None
    tool_selection: routing.ToolSelection = routing.ToolSelection()


@router.post("/tools/resolve")
def resolve_tools(body: ResolveIn):
    """선택 화면 미리보기 — LLM 없이 규칙만 적용. agent=auto 면 후보 agent 목록만 돌려준다."""
    skill = _or_404(skills.get_item(body.skill_id), "skill") if body.skill_id else None
    if body.agent_id not in catalog.AGENTS_BY_ID:
        return {"agent_id": catalog.AUTO, "candidates": routing.candidates(body.tool_selection, skill),
                "locked": routing.skill_tools(skill)}
    plan = routing.plan_tools(body.agent_id, body.tool_selection, skill)
    return {k: v for k, v in plan.event().items() if k not in ("type", "route_mode", "route_reason")}


@router.get("/overview")
async def get_overview(area: str = "M14 CMP"):
    return await service.overview(area)


# ── 사용자 · 메모리 ────────────────────────────────────────────

class MemoryIn(BaseModel):
    content: str = Field(min_length=1, max_length=memory.MAX_CHARS * 2)


@router.get("/me")
def get_me(user: dict = Depends(current_user)):
    m = user_store.get_memory(user["user_id"])
    return {"user": user, "memory": m, "memory_enabled": memory.ENABLED, "template": memory.template(user)}


@router.put("/me/memory")
def edit_memory(body: MemoryIn, user: dict = Depends(current_user)):
    """사용자가 화면에서 직접 고친 메모리 — 다음 대화부터 그대로 쓰인다."""
    return user_store.save_memory(user["user_id"], body.content.strip(), "edit")


@router.delete("/me/memory")
def reset_memory(user: dict = Depends(current_user)):
    """최신본만 지운다 (history 는 남김) — 다음 대화부터 새로 쌓인다."""
    user_store.delete_memory(user["user_id"])
    return {"ok": True}


@router.get("/me/memory/history")
def list_memory_history(user: dict = Depends(current_user)):
    return user_store.memory_history(user["user_id"])


@router.get("/me/memory/history/{version}")
def get_memory_version(version: int, user: dict = Depends(current_user)):
    return _or_404(user_store.memory_version(user["user_id"], version), "memory version")


@router.post("/me/memory/history/{version}/restore")
def restore_memory(version: int, user: dict = Depends(current_user)):
    old = _or_404(user_store.memory_version(user["user_id"], version), "memory version")
    return user_store.save_memory(user["user_id"], old["content"], "restore")


# ── 대화 ──────────────────────────────────────────────────────

@router.get("/conversations")
def list_conversations(source: Optional[str] = None, limit: int = 50):
    items = store.list_items("conversations")
    if source:
        items = [c for c in items if c.get("source") == source]
    items.sort(key=lambda c: c["updated_at"], reverse=True)
    return [service.conversation_head(c) for c in items[:limit]]


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: str):
    conv = _or_404(store.get_item("conversations", conv_id), "conversation")
    # trace(tool 원본 결과)는 다음 턴 agent 입력용 — 화면에는 tools 요약만 내려보낸다
    return conv | {"messages": [{k: v for k, v in m.items() if k != "trace"} for m in conv["messages"]]}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    if not store.delete_item("conversations", conv_id):
        raise HTTPException(404, "conversation not found")
    return {"ok": True}


# ── 스킬 ──────────────────────────────────────────────────────

class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = ""
    tools: list[str] = []
    instructions: str = ""


def _check_tools(names: list[str]) -> list[str]:
    # MCP 서버가 잠시 내려가 있어도 skill 편집은 되도록 catalog.yaml 에 있는 이름도 허용
    known = set(catalog.GROUPED_TOOLS) | set(catalog.TOOLS_BY_NAME)
    unknown = [n for n in names if n not in known]
    if unknown:
        raise HTTPException(422, f"unknown tools: {', '.join(unknown)}")
    return names


@router.get("/skills")
def list_skills():
    return skills.list_items()


@router.post("/skills")
def create_skill(body: SkillIn):
    _check_tools(body.tools)
    return skills.save(None, **body.model_dump())


@router.put("/skills/{skill_id}")
def update_skill(skill_id: str, body: SkillIn):
    _or_404(skills.get_item(skill_id), "skill")
    _check_tools(body.tools)
    return skills.save(skill_id, **body.model_dump())


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str):
    if not skills.delete_item(skill_id):
        raise HTTPException(404, "skill not found")
    return {"ok": True}


# ── 이벤터 ────────────────────────────────────────────────────

class Schedule(BaseModel):
    kind: str = Field(pattern="^(daily|weekly)$")
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    weekday: Optional[int] = Field(default=None, ge=0, le=6)


class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    schedule: Schedule
    prompt: str = ""
    skill_id: Optional[str] = None
    agent_id: str = "auto"
    target: str = ""
    enabled: bool = True


class EventPatch(BaseModel):
    enabled: bool


@router.get("/events")
def list_events():
    return [service.event_view(e) for e in store.list_items("events")]


@router.post("/events")
def create_event(body: EventIn):
    event = body.model_dump() | {"id": store.new_id("ev"), "last_run": None}
    return service.event_view(store.upsert_item("events", event))


@router.put("/events/{event_id}")
def update_event(event_id: str, body: EventIn):
    event = _or_404(store.get_item("events", event_id), "event")
    event.update(body.model_dump())
    return service.event_view(store.upsert_item("events", event))


@router.patch("/events/{event_id}")
def toggle_event(event_id: str, body: EventPatch):
    event = _or_404(store.get_item("events", event_id), "event")
    event["enabled"] = body.enabled
    return service.event_view(store.upsert_item("events", event))


@router.delete("/events/{event_id}")
def delete_event(event_id: str):
    if not store.delete_item("events", event_id):
        raise HTTPException(404, "event not found")
    return {"ok": True}


@router.post("/events/{event_id}/run")
async def run_event(event_id: str):
    _or_404(store.get_item("events", event_id), "event")
    return await service.run_event(event_id)
