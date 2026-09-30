from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub import catalog, service, store

router = APIRouter(prefix="/api/hub", tags=["hub"])


def _or_404(item: Optional[dict], what: str) -> dict:
    if item is None:
        raise HTTPException(404, f"{what} not found")
    return item


# ── 메타 / 대시보드 ───────────────────────────────────────────

@router.get("/meta")
def get_meta():
    return catalog.meta()


@router.get("/overview")
def get_overview(area: str = "M14 CMP"):
    return service.overview(area)


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
    return _or_404(store.get_item("conversations", conv_id), "conversation")


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
    unknown = [n for n in names if n not in catalog.TOOLS_BY_NAME]
    if unknown:
        raise HTTPException(422, f"unknown tools: {', '.join(unknown)}")
    return names


@router.get("/skills")
def list_skills():
    return store.list_items("skills")


@router.post("/skills")
def create_skill(body: SkillIn):
    ts = store.now_iso()
    skill = body.model_dump() | {"id": store.new_id("sk"), "uses": 0, "created_at": ts, "updated_at": ts}
    _check_tools(skill["tools"])
    return store.upsert_item("skills", skill)


@router.put("/skills/{skill_id}")
def update_skill(skill_id: str, body: SkillIn):
    skill = _or_404(store.get_item("skills", skill_id), "skill")
    _check_tools(body.tools)
    skill.update(body.model_dump(), updated_at=store.now_iso())
    return store.upsert_item("skills", skill)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str):
    if not store.delete_item("skills", skill_id):
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
