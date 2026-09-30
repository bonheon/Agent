"""
POST /api/chat — SSE 스트리밍.

이벤트 (data: <json>):
  {"type": "meta", "conversation_id"}          첫 이벤트
  {"type": "tool_start", "id", "name", "args"}
  {"type": "tool_end", "id", "name", "ms", "ok"}
  {"type": "delta", "delta"}                   텍스트 토큰
  {"type": "error", "message"}
  [DONE]
응답이 끝나면 대화가 hub 저장소에 기록된다.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import agent
from hub import service, store

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger("chat")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    conversation_id: Optional[str] = None
    agent_id: str = "auto"
    skill_id: Optional[str] = None


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest):
    conv_id = req.conversation_id or store.new_id("cv")
    messages = [m.model_dump() for m in req.messages]
    user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    async def generate():
        yield _sse({"type": "meta", "conversation_id": conv_id})
        text: list[str] = []
        runs: dict[str, dict] = {}
        try:
            async for ev in agent.stream(messages, req.agent_id, req.skill_id):
                if ev["type"] == "delta":
                    text.append(ev["text"])
                    yield _sse({"type": "delta", "delta": ev["text"]})
                    continue
                if ev["type"] == "tool_start":
                    runs[ev["id"]] = {"name": ev["name"], "args": ev["args"], "ms": None, "ok": None}
                elif ev["type"] == "tool_end" and ev["id"] in runs:
                    runs[ev["id"]].update(ms=ev["ms"], ok=ev["ok"])
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            log.exception("chat failed")
            yield _sse({"type": "error", "message": str(e)[:300]})
        finally:
            if text or runs:
                service.save_turn(conv_id, user_text, "".join(text), list(runs.values()),
                                  req.agent_id, req.skill_id)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
