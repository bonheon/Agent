"""
Hub JSON 파일 저장소 — 대화 / 스킬 / 이벤터.

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
COLLECTIONS = ("conversations", "skills", "events")

_lock = threading.Lock()
_cache: Optional[dict] = None


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _seed() -> dict:
    ts = now_iso()
    skills = [
        {
            "id": "sk_morning", "name": "출근 전 라인 점검",
            "description": "전일 이슈 + 현재 WIP + Open Hold 를 한 번에 정리",
            "tools": ["get_daily_report", "get_wip_status", "get_lot_hold_info"],
            "instructions": (
                "1. 전일 이슈 리포트로 P1~P2 항목을 먼저 확인한다.\n"
                "2. P1 이 장비 DOWN 이면 해당 Area 의 현재 WIP 를 조회해 대기 WIP 를 함께 보고한다.\n"
                "3. Open Hold 가 있으면 Lot 별 원인을 표로 정리한다.\n"
                "4. 마지막에 오늘 우선 대응 3가지를 한 줄씩 제안한다."
            ),
            "uses": 0, "created_at": ts, "updated_at": ts,
        },
        {
            "id": "sk_defect", "name": "Defect 원인 추적",
            "description": "Defect Map → Step Overlay → 수율 영향 순으로 원인 추적",
            "tools": ["get_defect_map", "get_defect_step_overlay", "get_defect_yield_history"],
            "instructions": (
                "1. Defect Map 으로 유형별 건수와 분포를 확인한다.\n"
                "2. 가장 많은 유형이 있는 wafer 로 Step 간 Overlay 를 조회해 발생 step 을 찾는다.\n"
                "3. 해당 유형의 수율 이력으로 kill rate 를 확인하고 결론을 3줄로 정리한다."
            ),
            "uses": 0, "created_at": ts, "updated_at": ts,
        },
        {
            "id": "sk_yield", "name": "수율 브리핑",
            "description": "전체 Lot Recipe/Equipment 기준 수율 비교",
            "tools": ["analyze_yield_grouping", "get_wafer_map"],
            "instructions": (
                "Lot 을 지정하지 않으면 TE2FE35~TE2FE42 전체를 recipe 기준으로 비교하고,\n"
                "평균이 가장 낮은 그룹을 짚어 원인 후보를 제시한다."
            ),
            "uses": 0, "created_at": ts, "updated_at": ts,
        },
    ]
    events = [
        {
            "id": "ev_daily", "name": "전일 이슈 리포트",
            "schedule": {"kind": "daily", "time": "07:30", "weekday": None},
            "skill_id": "sk_morning", "agent_id": "line",
            "prompt": "M14 CMP 전일 이슈 정리해줘",
            "target": "Cube #CMP-일일현황", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_noon", "name": "오전 장비 이상 요약",
            "schedule": {"kind": "daily", "time": "13:00", "weekday": None},
            "skill_id": None, "agent_id": "line",
            "prompt": "M14 CMP 지금 DOWN·PM 장비와 대기 WIP 정리해줘",
            "target": "팀 메일", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_eod", "name": "WIP EOD 점검",
            "schedule": {"kind": "daily", "time": "17:00", "weekday": None},
            "skill_id": None, "agent_id": "line",
            "prompt": "M14 CMP EOD 이동 예상과 병목 공정 알려줘",
            "target": "Cube #CMP-일일현황", "enabled": True, "last_run": None,
        },
        {
            "id": "ev_weekly", "name": "주간 수율 브리핑",
            "schedule": {"kind": "weekly", "time": "17:00", "weekday": 4},
            "skill_id": "sk_yield", "agent_id": "yield",
            "prompt": "이번 주 전체 Lot 수율 브리핑해줘",
            "target": "PPT 초안", "enabled": False, "last_run": None,
        },
    ]
    return {"conversations": [], "skills": skills, "events": events}


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
