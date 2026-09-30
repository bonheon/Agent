"""
Hub 정적 카탈로그 — 에이전트 프리셋, tool 표시 정보, 포탈 목록.

에이전트 = tool 부분집합 + 역할 설명.
tool 이 늘어날수록 LLM 의 tool 선택 정확도가 떨어지므로, 에이전트/스킬 단위로
후보 tool 수를 줄여 주는 것이 이 구조의 목적이다.
"""
from tools.langgraph_tools import TOOLS
from tools.wip_tools import list_supported_areas

TOOLS_BY_NAME = {t.name: t for t in TOOLS}

# name → (화면 표시명, 분류)
TOOL_META: dict[str, tuple[str, str]] = {
    "get_daily_report":         ("전일 이슈 리포트", "라인 운영"),
    "get_wip_status":           ("WIP 현황", "라인 운영"),
    "get_lot_hold_info":        ("Lot Hold 조회", "라인 운영"),
    "get_defect_map":           ("Defect Map", "Defect"),
    "get_defect_trend":         ("Defect Trend", "Defect"),
    "get_defect_step_overlay":  ("Step 간 Overlay", "Defect"),
    "get_yield_defect":         ("Wafer 수율 Chip Kill", "수율 · 계측"),
    "get_defect_yield_history": ("Defect 수율 이력", "수율 · 계측"),
    "analyze_yield_grouping":   ("수율 Grouping", "수율 · 계측"),
    "get_wafer_map":            ("Wafer Map", "수율 · 계측"),
    "get_lot_trend":            ("공정 지표 Trend", "수율 · 계측"),
}

AGENTS: list[dict] = [
    {
        "id": "auto",
        "name": "자동 선택",
        "description": "전체 tool 중에서 에이전트가 직접 고릅니다",
        "tools": [t.name for t in TOOLS],
    },
    {
        "id": "line",
        "name": "라인 운영",
        "description": "WIP · Hold · 전일 이슈 · 장비 상태",
        "tools": ["get_daily_report", "get_wip_status", "get_lot_hold_info"],
    },
    {
        "id": "defect",
        "name": "Defect 분석",
        "description": "Defect 위치 · 추이 · step 간 이동 · 수율 영향",
        "tools": [
            "get_defect_map", "get_defect_trend", "get_defect_step_overlay",
            "get_yield_defect", "get_defect_yield_history",
        ],
    },
    {
        "id": "yield",
        "name": "수율 분석",
        "description": "Lot 수율 Grouping · Wafer 수율 · 계측 트렌드",
        "tools": [
            "analyze_yield_grouping", "get_yield_defect", "get_defect_yield_history",
            "get_wafer_map", "get_lot_trend",
        ],
    },
]
AGENTS_BY_ID = {a["id"]: a for a in AGENTS}

# 외부 포탈 — 실제 health check 연동 전까지 Mock 상태
PORTALS: list[dict] = [
    {"id": "mico", "name": "MICO", "description": "CMP 공정 최적화 알고리즘", "status": "ok", "note": "정상", "url": "#"},
    {"id": "siria", "name": "Siria", "description": "라인 운영 RAG 에이전트", "status": "ok", "note": "3.2s", "url": "#"},
    {"id": "datahub", "name": "DataHub", "description": "실시간 라인 모니터링", "status": "warn", "note": "수집 지연 4분", "url": "#"},
    {"id": "algo", "name": "알고리즘 관리", "description": "알고리즘 등록 · 배포", "status": "err", "note": "점검중", "url": "#"},
]


def tool_info(name: str) -> dict:
    label, category = TOOL_META.get(name, (name, "기타"))
    tool = TOOLS_BY_NAME[name]
    # docstring 첫 문단만 — Args 등은 화면에 불필요
    desc = (tool.description or "").strip().split("\n\n")[0].split("\n")[0]
    return {"name": name, "label": label, "category": category, "description": desc}


def meta() -> dict:
    return {
        "agents": AGENTS,
        "tools": [tool_info(t.name) for t in TOOLS],
        "areas": list_supported_areas(),
        "portals": PORTALS,
    }
