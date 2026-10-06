"""
Hub 카탈로그 — tool 원천, tool 그룹, agent 정의, 포탈 목록.

agent/group 정의는 catalog.yaml 에 있다 (기준: group = 데이터 영역, agent = 업무 방식).
tool 원천은 MCP 서버(mcp_servers.yaml)다. refresh() 가 서버에서 다시 받아와
TOOLS_BY_NAME 을 제자리에서 갱신한다 — 다른 모듈이 import 한 dict 참조가 그대로 유효하도록.
"""
import logging
from pathlib import Path

import yaml

from hub import mcp_registry
from tools.wip_tools import list_supported_areas

log = logging.getLogger("catalog")

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.yaml"
AUTO = "auto"


# MCP 에서 받아온 tool — refresh() 전에는 비어 있다.
# 서버 장애로 빠진 tool 은 여기 없으므로 routing 에서 자동으로 "unavailable" 이 된다.
TOOLS_BY_NAME: dict = {}
VERSION = 0  # refresh 마다 증가 — agent 그래프 캐시 키에 포함해 낡은 tool 객체를 버린다

# name → 화면 표시명
TOOL_LABELS: dict[str, str] = {
    "get_daily_report":         "전일 이슈 리포트",
    "get_wip_status":           "WIP 현황",
    "get_lot_hold_info":        "Lot Hold 조회",
    "get_lot_trend":            "공정 지표 Trend",
    "get_defect_map":           "Defect Map",
    "get_defect_trend":         "Defect Trend",
    "get_defect_step_overlay":  "Step 간 Overlay",
    "get_yield_defect":         "Wafer 수율 Chip Kill",
    "get_defect_yield_history": "Defect 수율 이력",
    "analyze_yield_grouping":   "수율 Grouping",
    "get_wafer_map":            "Wafer Map",
}


def _load_catalog() -> tuple[list[dict], list[dict]]:
    raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    groups, agents = raw["groups"], raw["agents"]
    group_ids = {g["id"] for g in groups}
    for a in agents:
        for gid in a["allowed_groups"] + a["default_groups"]:
            if gid not in group_ids:
                raise ValueError(f"agent '{a['id']}': unknown group '{gid}'")
        if not set(a["default_groups"]) <= set(a["allowed_groups"]):
            raise ValueError(f"agent '{a['id']}': default_groups 는 allowed_groups 안에 있어야 함")
    return groups, agents


GROUPS, AGENTS = _load_catalog()
GROUPS_BY_ID = {g["id"]: g for g in GROUPS}
AGENTS_BY_ID = {a["id"]: a for a in AGENTS}
FALLBACK_AGENT = AGENTS[0]["id"]

# tool → 소속 group (화면 분류용, 여러 group 에 속하면 첫 번째)
_GROUP_OF: dict[str, str] = {}
for _g in GROUPS:
    for _n in _g["tools"]:
        _GROUP_OF.setdefault(_n, _g["id"])


GROUPED_TOOLS = list(dict.fromkeys(n for g in GROUPS for n in g["tools"]))


def _check_tools() -> None:
    """yaml 과 MCP 가 어긋나면 기동은 하되 경고를 남긴다."""
    # 서버가 내려가 있으면 refresh 마다 반복되므로 한 줄로 모아서 남긴다
    missing = [n for n in GROUPED_TOOLS if n not in TOOLS_BY_NAME]
    if missing:
        log.warning("catalog.yaml 의 tool %d개를 MCP 에서 찾지 못함 — 사용 불가로 취급: %s", len(missing), ", ".join(missing))
    ungrouped = [n for n in TOOLS_BY_NAME if n not in _GROUP_OF]
    if ungrouped:
        log.warning("어떤 group 에도 없는 MCP tool — agent 가 쓰려면 catalog.yaml 에 추가: %s", ", ".join(ungrouped))


async def refresh() -> dict:
    """MCP 서버에서 tool 을 다시 받아온다. 서버가 전부 죽어 있어도 예외 없이 빈 목록으로 동작."""
    global VERSION
    tools = await mcp_registry.load_tools()
    TOOLS_BY_NAME.clear()
    TOOLS_BY_NAME.update(tools)
    VERSION += 1
    _check_tools()
    log.info("MCP tool %d개 로드 (%s)", len(tools),
             ", ".join(f"{s['name']}={s['status']}" for s in mcp_registry.status()))
    return {"tools": len(tools), "servers": mcp_registry.status()}


def group_tools(group_ids) -> list[str]:
    """group 들의 tool 을 정의 순서대로, 중복 없이."""
    seen: dict[str, None] = {}
    for gid in group_ids:
        for name in GROUPS_BY_ID[gid]["tools"] if gid in GROUPS_BY_ID else []:
            seen.setdefault(name)
    return list(seen)


def agent_pool(agent_id: str) -> list[str]:
    """agent 가 쓸 수 있는 tool 전체 (allowed_groups)."""
    return group_tools(AGENTS_BY_ID[agent_id]["allowed_groups"])


def agent_defaults(agent_id: str) -> list[str]:
    return group_tools(AGENTS_BY_ID[agent_id]["default_groups"])


# 외부 포탈 — 실제 health check 연동 전까지 Mock 상태
PORTALS: list[dict] = [
    {"id": "mico", "name": "MICO", "description": "CMP 공정 최적화 알고리즘", "status": "ok", "note": "정상", "url": "#"},
    {"id": "siria", "name": "Siria", "description": "라인 운영 RAG 에이전트", "status": "ok", "note": "3.2s", "url": "#"},
    {"id": "datahub", "name": "DataHub", "description": "실시간 라인 모니터링", "status": "warn", "note": "수집 지연 4분", "url": "#"},
    {"id": "algo", "name": "알고리즘 관리", "description": "알고리즘 등록 · 배포", "status": "err", "note": "점검중", "url": "#"},
]


def _server_of(name: str):
    return next((s["name"] for s in mcp_registry.status() if name in s["tools"]), None)


def tool_info(name: str) -> dict:
    tool = TOOLS_BY_NAME.get(name)
    # docstring 첫 문단만 — Args 등은 화면에 불필요
    desc = (tool.description or "").strip().split("\n\n")[0].split("\n")[0] if tool else ""
    gid = _GROUP_OF.get(name)
    return {
        "name": name, "label": TOOL_LABELS.get(name, name),
        "group": gid, "category": GROUPS_BY_ID[gid]["name"] if gid else "기타",
        "description": desc, "available": tool is not None, "server": _server_of(name),
    }


def _agent_view(a: dict) -> dict:
    return {
        "id": a["id"], "name": a["name"], "description": a["description"],
        "tools": agent_pool(a["id"]),
        "allowed_groups": a["allowed_groups"], "default_groups": a["default_groups"],
    }


def meta() -> dict:
    auto = {
        "id": AUTO, "name": "자동 선택", "description": "질문을 보고 agent 를 고릅니다",
        "tools": GROUPED_TOOLS, "allowed_groups": [g["id"] for g in GROUPS], "default_groups": [],
    }
    # 그룹에 없는 MCP tool 도 보여준다 (group=None, "기타") — catalog.yaml 에 추가하라는 신호
    names = GROUPED_TOOLS + [n for n in TOOLS_BY_NAME if n not in _GROUP_OF]
    return {
        "agents": [auto] + [_agent_view(a) for a in AGENTS],
        "groups": GROUPS,
        "tools": [tool_info(n) for n in names],
        "areas": list_supported_areas(),
        "portals": PORTALS,
        "mcp_servers": mcp_registry.status(),
    }
