"""
Hub 도메인 로직 — 대화 기록, 이벤터 실행/스케줄, 홈 대시보드 요약.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from hub import store
from tools.daily_report_tools import get_daily_report
from tools.wip_tools import get_wip_status

log = logging.getLogger("hub")

_TAG_RE = re.compile(r"\[[A-Z_]+:[^\]]+\]")
_MD_RE = re.compile(r"[#*`>|_~-]+")


def summarize(text: str, limit: int = 90) -> str:
    """대화 목록에 보일 한 줄 요약 — 차트 태그와 마크다운 기호를 걷어낸 첫 문장."""
    plain = _MD_RE.sub(" ", _TAG_RE.sub("", text))
    plain = " ".join(plain.split())
    return plain[:limit] + ("…" if len(plain) > limit else "")


# ── 대화 ──────────────────────────────────────────────────────

def conversation_head(conv: dict) -> dict:
    """목록용 — messages 제외."""
    return {k: v for k, v in conv.items() if k != "messages"} | {"turns": len(conv["messages"]) // 2}


def save_turn(
    conv_id: Optional[str], user_text: str, assistant_text: str, tools: list[dict],
    agent_id: str, skill_id: Optional[str], source: str = "chat", event_id: Optional[str] = None,
) -> dict:
    ts = store.now_iso()
    conv = store.get_item("conversations", conv_id) if conv_id else None
    if conv is None:
        conv = {
            "id": conv_id or store.new_id("cv"),
            "title": summarize(user_text, 40),
            "source": source, "event_id": event_id,
            "created_at": ts, "messages": [],
        }
    conv["messages"] += [
        {"role": "user", "content": user_text, "at": ts},
        {"role": "assistant", "content": assistant_text, "tools": tools, "at": ts},
    ]
    conv.update(agent_id=agent_id, skill_id=skill_id, updated_at=ts, summary=summarize(assistant_text))
    store.upsert_item("conversations", conv)

    if skill_id and (skill := store.get_item("skills", skill_id)):
        skill["uses"] = skill.get("uses", 0) + 1
        store.upsert_item("skills", skill)
    return conv


# ── 이벤터 ────────────────────────────────────────────────────

def next_run(event: dict, now: Optional[datetime] = None) -> Optional[str]:
    if not event["enabled"]:
        return None
    now = now or datetime.now()
    hh, mm = map(int, event["schedule"]["time"].split(":"))
    cand = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    weekday = event["schedule"].get("weekday") if event["schedule"]["kind"] == "weekly" else None
    for _ in range(8):
        if cand > now and (weekday is None or cand.weekday() == weekday):
            return cand.isoformat(timespec="minutes")
        cand = (cand + timedelta(days=1)).replace(hour=hh, minute=mm)
    return None


def event_view(event: dict) -> dict:
    return event | {"next_run": next_run(event)}


async def run_event(event_id: str) -> dict:
    """이벤트를 지금 실행하고 결과 대화를 저장한다."""
    import agent  # 순환 import 방지 — agent 가 hub.store 를 쓴다

    event = store.get_item("events", event_id)
    if event is None:
        raise KeyError(event_id)

    skill = store.get_item("skills", event["skill_id"]) if event.get("skill_id") else None
    prompt = event.get("prompt") or (f"'{skill['name']}' 스킬을 실행해줘" if skill else event["name"])
    started = datetime.now()
    try:
        text, tools = await agent.run([{"role": "user", "content": prompt}], event.get("agent_id"), event.get("skill_id"))
        conv = save_turn(None, prompt, text, tools, event.get("agent_id") or "auto", event.get("skill_id"),
                         source="event", event_id=event_id)
        conv["title"] = event["name"]
        store.upsert_item("conversations", conv)
        event["last_run"] = {
            "at": started.isoformat(timespec="seconds"), "status": "ok",
            "conversation_id": conv["id"], "summary": conv["summary"],
            "tool_count": len(tools), "elapsed_s": round((datetime.now() - started).total_seconds(), 1),
        }
    except Exception as e:  # noqa: BLE001 — 실패도 기록으로 남긴다
        log.exception("event %s failed", event_id)
        event["last_run"] = {
            "at": started.isoformat(timespec="seconds"), "status": "error",
            "conversation_id": None, "summary": str(e)[:200], "tool_count": 0,
            "elapsed_s": round((datetime.now() - started).total_seconds(), 1),
        }
    store.upsert_item("events", event)
    return event_view(event)


async def scheduler_loop(interval_s: int = 30) -> None:
    """HUB_SCHEDULER=1 일 때만 main.py 가 띄운다. 분 단위로 도래한 이벤트를 실행."""
    fired: set[str] = set()
    while True:
        now = datetime.now()
        stamp = now.strftime("%Y-%m-%dT%H:%M")
        for ev in store.list_items("events"):
            sch = ev["schedule"]
            due = ev["enabled"] and sch["time"] == now.strftime("%H:%M") and (
                sch["kind"] == "daily" or sch.get("weekday") == now.weekday()
            )
            key = f"{ev['id']}@{stamp}"
            if due and key not in fired:
                fired.add(key)
                asyncio.create_task(run_event(ev["id"]))
        await asyncio.sleep(interval_s)


# ── 홈 대시보드 ────────────────────────────────────────────────

def overview(area: str) -> dict:
    wip = get_wip_status(area)
    report = get_daily_report(area)
    kpi = report["kpi"]

    groups, down_eq = [], []
    for g in wip["process_groups"]:
        counts: dict[str, int] = {}
        for e in g["equipments"]:
            counts[e["status"]] = counts.get(e["status"], 0) + 1
            if e["status"] == "DOWN":
                down_eq.append(e["eq_id"])
        groups.append({
            "name": g["group_name"], "wip": g["wip_total"],
            "running": g["wip_running"], "queue": g["wip_queue"],
            "move_actual": g["move_actual"], "move_target": g["move_target"],
            "achieve_pct": g["achieve_pct"], "equipment": counts, "eq_total": len(g["equipments"]),
        })

    return {
        "area": wip["area_key"],
        "updated_at": wip["timestamp"],
        "report_date": report["report_date"],
        "kpi": {
            "wip": wip["total_wip"], "wip_delta": kpi["wip_delta"],
            "move_actual": wip["total_move_actual"], "move_target": wip["total_move_target"],
            "move_projected": wip["total_move_projected"], "achieve_pct": wip["total_achieve_pct"],
            "open_holds": kpi["open_holds"], "new_holds": kpi["new_holds"],
            "down_count": len(down_eq), "down_eq": down_eq,
        },
        "actions": [
            {k: a[k] for k in ("priority", "urgency", "category", "target", "summary", "suggested_action")}
            for a in report["priority_actions"][:5]
        ],
        "groups": groups,
    }
