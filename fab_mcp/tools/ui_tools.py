"""
화면 전용 tool — 허브의 차트 · 대시보드 API 가 MCP 로 호출한다. LLM 에는 묶이지 않는다.

LLM 용 tool(langgraph_tools.py)은 토큰을 아끼려고 요약을 돌려주지만, 차트를 그리려면
좌표 · 시계열 전체가 필요하다. 그래서 같은 데이터를 "화면용 전체본" 으로 따로 노출한다.
허브 catalog.yaml 의 ui_tools 에 이름이 있어야 하고, 이름은 ui_ 로 시작한다.

회사 MCP 로 옮길 때는 같은 이름 · 인자 · 반환 모양(JSON)으로 제공하면 허브 수정 없이 붙는다.
"""
import json
from typing import Optional

from tools.daily_report_tools import get_daily_report
from tools.db_tools import (
    _mock_defect_map,
    _mock_defect_review,
    _mock_defect_step_overlay,
    _mock_defect_trend_full,
    _mock_defect_yield_history,
    _mock_lot_trend_full,
    _mock_wafer_map,
    _mock_yield_defect,
)
from tools.wip_tools import get_wip_status, list_supported_areas
from tools.yield_tools import (
    FAIL_PARAMS,
    GROUPING_COLUMNS,
    PASS_PARAMS,
    YIELD_PARAMS_META,
    analyze_yield,
    get_all_lots,
)


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


# ── 차트 ──────────────────────────────────────────────────────

def ui_wafer_map(lot_id: str) -> str:
    """[화면용] Lot 의 wafer map 전체 데이터."""
    return _json(_mock_wafer_map(lot_id))


def ui_lot_trend(lot_id: str, metric: str = "thickness") -> str:
    """[화면용] 공정 지표 trend 전체 시계열."""
    return _json(_mock_lot_trend_full(lot_id, metric))


def ui_defect_map(lot_id: str, wafer_no: int) -> str:
    """[화면용] wafer 1장의 defect 좌표 전체."""
    return _json(_mock_defect_map(lot_id, wafer_no))


def ui_defect_review(lot_id: str, wafer_no: int, defect_id: str) -> str:
    """[화면용] defect 1개의 review 이미지와 상세."""
    return _json(_mock_defect_review(lot_id, wafer_no, defect_id))


def ui_defect_trend(lot_id: str, defect_type: str) -> str:
    """[화면용] defect 유형별 trend 전체 시계열."""
    return _json(_mock_defect_trend_full(lot_id, defect_type))


def ui_yield_defect(lot_id: str, wafer_no: int) -> str:
    """[화면용] wafer 수율 bin map + defect overlay."""
    return _json(_mock_yield_defect(lot_id, wafer_no))


def ui_defect_yield_history(lot_id: str, defect_type: str) -> str:
    """[화면용] defect 건수 vs 수율 이력 전체."""
    return _json(_mock_defect_yield_history(lot_id, defect_type))


def ui_defect_step_overlay(lot_id: str, wafer_no: int) -> str:
    """[화면용] step 간 defect overlay 전체."""
    return _json(_mock_defect_step_overlay(lot_id, wafer_no))


# ── 라인 현황 ─────────────────────────────────────────────────

def ui_wip_status(area_key: str) -> str:
    """[화면용] area 의 WIP · 장비 status · move 실적 전체."""
    return _json(get_wip_status(area_key))


def ui_wip_areas() -> str:
    """[화면용] 지원 area 목록."""
    return _json(list_supported_areas())


def ui_daily_report(area_key: str, report_date: Optional[str] = None) -> str:
    """[화면용] 전일 이슈 리포트 전체."""
    return _json(get_daily_report(area_key, report_date))


# ── 수율 분석 ─────────────────────────────────────────────────

def ui_yield_lots() -> str:
    """[화면용] 수율 분석 가능한 Lot 목록."""
    return _json(get_all_lots())


def ui_yield_meta() -> str:
    """[화면용] 수율 분석 grouping 기준 · 파라미터 정의."""
    return _json({"grouping_columns": GROUPING_COLUMNS, "yield_params": YIELD_PARAMS_META,
                  "pass_params": PASS_PARAMS, "fail_params": FAIL_PARAMS})


def ui_yield_analyze(lot_ids: list[str], group_by: str, yield_params: list[str]) -> str:
    """[화면용] Lot grouping 수율 분석 전체 결과."""
    return _json(analyze_yield(lot_ids, group_by, yield_params))


UI_TOOLS = [
    ui_wafer_map, ui_lot_trend, ui_defect_map, ui_defect_review, ui_defect_trend,
    ui_yield_defect, ui_defect_yield_history, ui_defect_step_overlay,
    ui_wip_status, ui_wip_areas, ui_daily_report,
    ui_yield_lots, ui_yield_meta, ui_yield_analyze,
]
