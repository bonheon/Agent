"""
Hub JSON 파일 저장소 — 대화 / 스킬 사용 기록 / 이벤터.

사내 DB 연동 전까지 backend/data/hub.json 한 파일에 저장한다.
프로세스 하나(uvicorn 단일 worker) 기준이며, 쓰기는 lock 으로 직렬화한다.
"""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "hub.json"
# skills 는 SKILL.md 폴더로 옮겼다(hub/skills.py) — 남은 "skills" 는 이전 데이터 이관용으로만 읽는다
COLLECTIONS = ("conversations", "skills", "skill_stats", "events")

_lock = threading.Lock()
_cache: Optional[dict] = None


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _seed() -> dict:
    events = [
        {
            "id": "ev_daily", "name": "전일 이슈 리포트",
            "schedule": {"kind": "daily", "time": "07:30", "weekday": None},
            "skill_id": "sk_morning", "agent_id": "auto",
            "prompt": "M14 CMP 전일 이슈 정리해줘",
            "target": "Cube #CMP-일일현황", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_noon", "name": "오전 장비 이상 요약",
            "schedule": {"kind": "daily", "time": "13:00", "weekday": None},
            "skill_id": None, "agent_id": "auto",
            "prompt": "M14 CMP 지금 DOWN·PM 장비와 대기 WIP 정리해줘",
            "target": "팀 메일", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_eod", "name": "WIP EOD 점검",
            "schedule": {"kind": "daily", "time": "17:00", "weekday": None},
            "skill_id": None, "agent_id": "auto",
            "prompt": "M14 CMP EOD 이동 예상과 병목 공정 알려줘",
            "target": "Cube #CMP-일일현황", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_weekly", "name": "주간 수율 브리핑",
            "schedule": {"kind": "weekly", "time": "17:00", "weekday": 4},
            "skill_id": "sk_yield", "agent_id": "auto",
            "prompt": "이번 주 전체 Lot 수율 브리핑해줘",
            "target": "PPT 초안", "enabled": False, "last_run": None,
        },
    ]
    return {"conversations": [], "events": events}


def _load() -> dict:
    global _cache
    if _cache is None:
        if DATA_PATH.exists():
            _cache = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            for c in COLLECTIONS:
                _cache.setdefault(c, [])
        else:
            _cache = _seed()
            _flush()
    return _cache


def _flush() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_PATH)


def list_items(coll: str) -> list[dict]:
    with _lock:
        return [dict(x) for x in _load()[coll]]


def get_item(coll: str, item_id: str) -> Optional[dict]:
    with _lock:
        for x in _load()[coll]:
            if x["id"] == item_id:
                return dict(x)
    return None


def upsert_item(coll: str, item: dict) -> dict:
    with _lock:
        items = _load()[coll]
        for i, x in enumerate(items):
            if x["id"] == item["id"]:
                items[i] = item
                break
        else:
            items.insert(0, item)
        _flush()
    return item


def delete_item(coll: str, item_id: str) -> bool:
    with _lock:
        items = _load()[coll]
        n = len(items)
        items[:] = [x for x in items if x["id"] != item_id]
        if len(items) != n:
            _flush()
            return True
    return False
