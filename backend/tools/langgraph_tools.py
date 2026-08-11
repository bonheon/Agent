"""
LangGraph/LangChain tool 정의 모음.
회사 DB 연동 전까지는 db_tools.py 등의 Mock 데이터 생성기를 감싸는 LangChain @tool로 노출합니다.

신규 tool 추가 방법:
  1. 이 파일에 @tool 데코레이터 함수를 추가 (docstring이 LLM에 전달되는 설명)
  2. 하단 TOOLS 리스트에 등록
그 외 chat.py, main.py 수정 불필요 — TOOLS는 langgraph_agent.py에서 자동으로 바인딩됩니다.
"""
import json
from typing import Literal, Optional

from langchain_core.tools import tool

from tools.db_tools import (
    _mock_lot_hold_info,
    _mock_lot_trend_summary,
    _mock_wafer_map_summary,
    _mock_defect_summary,
    _mock_defect_map,
    _mock_defect_trend_summary,
    _mock_yield_defect_summary,
    _mock_defect_yield_history,
    _mock_defect_step_overlay,
)
from tools.yield_tools import analyze_yield as _analyze_yield
from tools.wip_tools import get_wip_status as _get_wip_status
from tools.daily_report_tools import get_daily_report as _get_daily_report

Metric = Literal["thickness", "cd", "particle_count"]
DefectType = Literal["PARTICLE", "SCRATCH", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"]
GroupBy = Literal["recipe", "equipment", "process_id", "custom_group"]
YieldParam = Literal["PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner", "bl_lkg", "ledic"]


def _json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


@tool
def get_lot_hold_info(lot_id: str) -> str:
    """특정 Lot의 Hold 상태 및 원인을 조회합니다.

    Args:
        lot_id: 조회할 Lot ID (예: TE2FE35)
    """
    return _json(_mock_lot_hold_info(lot_id))


@tool
def get_lot_trend(lot_id: str, metric: Metric) -> str:
    """특정 Lot 주변 로트들의 공정 지표 트렌드를 1000포인트(40 Lot × 25 Slot) 규모로 조회합니다.

    Args:
        lot_id: 기준 Lot ID
        metric: 조회할 지표
    """
    return _json(_mock_lot_trend_summary(lot_id, metric))


@tool
def get_wafer_map(lot_id: str) -> str:
    """특정 Lot의 Wafer Map 데이터(Die 별 박막 두께)를 조회합니다.

    Args:
        lot_id: 조회할 Lot ID
    """
    return _json(_mock_wafer_map_summary(lot_id))


@tool
def get_defect_map(lot_id: str, wafer_no: Optional[int] = None) -> str:
    """특정 Lot의 Defect Out 현황 및 Wafer별 Defect Map 데이터를 조회합니다.

    Args:
        lot_id: 조회할 Lot ID
        wafer_no: 특정 wafer 번호 (생략 시 전체 요약)
    """
    result = _mock_defect_summary(lot_id) if wafer_no is None else _mock_defect_map(lot_id, wafer_no)
    return _json(result)


@tool
def get_defect_trend(lot_id: str, defect_type: DefectType) -> str:
    """특정 Defect 유형의 Lot별 발생 건수 Trend를 조회합니다.

    Args:
        lot_id: 조회할 Lot ID
        defect_type: 조회할 Defect 유형
    """
    return _json(_mock_defect_trend_summary(lot_id, defect_type))


@tool
def get_yield_defect(lot_id: str, wafer_no: int) -> str:
    """특정 Wafer의 수율(Bin) 데이터와 Defect 위치를 조회하여 단일 Wafer의 Chip Kill 분석을 수행합니다.

    Args:
        lot_id: 조회할 Lot ID
        wafer_no: 조회할 wafer 번호
    """
    return _json(_mock_yield_defect_summary(lot_id, wafer_no))


@tool
def get_defect_yield_history(lot_id: str, defect_type: DefectType) -> str:
    """특정 Defect 유형이 Lot 내 전체 Wafer(슬롯)의 수율에 미치는 영향을 분석합니다.
    현재 wafer의 수율이 아직 나오지 않은 경우에도 다른 슬롯 이력으로 chip kill 가능성을
    추정할 때 사용하세요. 상관계수, 슬롯별 defect 건수 vs 수율, 평균 chip kill rate를 제공합니다.

    Args:
        lot_id: 조회할 Lot ID
        defect_type: 분석할 Defect 유형
    """
    full = _mock_defect_yield_history(lot_id, defect_type)
    corr = full["correlation"]
    result = {
        "lot_id": full["lot_id"],
        "defect_type": full["defect_type"],
        "correlation": corr,
        "avg_yield_pct": full["avg_yield_pct"],
        "avg_kill_rate_pct": full["avg_kill_rate_pct"],
        "high_risk_wafers": full["high_risk_wafers"],
        "chart_tag": f"[DEFECT_YIELD_HISTORY:{lot_id}:{defect_type}]",
        "interpretation": (
            f"상관계수 {corr} — "
            + ("강한 음의 상관: 해당 defect가 많을수록 수율이 낮아짐" if corr < -0.5 else
               "약한 상관" if abs(corr) < 0.3 else
               "중간 수준 상관")
        ),
    }
    return _json(result)


@tool
def analyze_yield_grouping(
    lot_ids: list[str],
    group_by: GroupBy,
    yield_params: Optional[list[YieldParam]] = None,
) -> str:
    """여러 Lot의 수율 데이터를 특정 기준으로 Grouping하여 그룹 간 수율 차이를 비교 분석합니다.
    Recipe, Equipment, Process ID, Custom Group 중 하나를 기준으로 그룹핑하고
    Pass rate(PT1H 계열)와 Fail rate(bl_lkg, ledic 등)를 비교합니다.
    의미 있는 비교를 위해 여러 Lot을 포함하세요. 사용 가능 Lot: TE2FE35~TE2FE42.

    Args:
        lot_ids: 분석할 Lot ID 목록 (2개 이상 권장)
        group_by: Grouping 기준
        yield_params: 분석할 수율 파라미터 (미지정 시 전체 사용)
    """
    params = yield_params or ["PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner", "bl_lkg", "ledic"]
    analysis = _analyze_yield(lot_ids, group_by, params)

    group_summaries = [
        {
            "group": g["group_value"],
            "wafer_count": g["count"],
            "stats": {
                p: {"mean": g["stats"][p]["mean"], "std": g["stats"][p]["std"]}
                for p in params
                if p in g["stats"]
            },
        }
        for g in analysis["groups"]
    ]

    tag = f"[YIELD_ANALYSIS:{','.join(lot_ids)}:{group_by}:{','.join(params)}]"
    result = {
        "group_by": group_by,
        "lot_ids": lot_ids,
        "total_wafers": analysis["total_wafers"],
        "group_count": len(analysis["groups"]),
        "groups": group_summaries,
        "chart_tag": tag,
        "instruction": f"그룹별 수율 차이를 간결하게 요약한 뒤 반드시 '{tag}' 태그를 응답에 포함하세요. 태그가 있어야 차트가 렌더링됩니다.",
    }
    return _json(result)


@tool
def get_daily_report(area_key: str, report_date: Optional[str] = None) -> str:
    """전일(또는 특정 일자) 공정 Area의 이슈를 종합 분석합니다.
    WIP 변동, Lot Hold 현황(건수/원인/공정별), Defect 스파이크, 장비 Down 이력,
    그리고 WIP·Hold·Defect·장비 Down을 교차 분석한 오늘의 우선 대응 액션 리스트를 제공합니다.
    '전일 이슈', '오늘 아침 보고', '어제 이슈 정리' 등의 요청에 사용하세요.

    Args:
        area_key: 조회 Area (예: 'M14 CMP', 'M14 Photo'). 명시 없으면 'M14 CMP' 사용.
        report_date: 조회 날짜 YYYY-MM-DD. 생략 시 전일.
    """
    data = _get_daily_report(area_key, report_date)
    kpi = data["kpi"]
    tag = f"[DAILY_REPORT:{area_key}]"
    top_actions = [
        {
            "priority": a["priority"],
            "urgency": a["urgency"],
            "category": a["category"],
            "target": a["target"],
            "summary": a["summary"],
        }
        for a in data["priority_actions"][:5]
    ]
    result = {
        "area": data["area_name"],
        "report_date": data["report_date"],
        "wip_delta": kpi["wip_delta"],
        "move_achieve_pct": kpi["move_achieve_pct"],
        "new_holds": kpi["new_holds"],
        "open_holds": kpi["open_holds"],
        "defect_spikes": kpi["defect_spike_count"],
        "down_equipment": kpi["still_down_count"],
        "priority_actions": top_actions,
        "chart_tag": tag,
        "instruction": (
            f"전일 이슈를 간결하게 요약하고 우선 대응 사항을 언급한 뒤 "
            f"반드시 '{tag}' 태그를 응답에 포함하세요. "
            "태그가 있어야 상세 리포트 카드가 렌더링됩니다."
        ),
    }
    return _json(result)


@tool
def get_wip_status(area_key: str) -> str:
    """특정 공정 Area의 WIP(Work In Progress) 현황을 조회합니다.
    공정 그룹별 WIP 재공량, 장비별 현재 Status(RUNNING/IDLE/DOWN/PM),
    오늘의 이동 목표 및 현재 실적, EOD(End of Day) 예상 이동량을 제공합니다.
    'M14 CMP', 'M14 Photo' 등 Area 이름으로 조회하세요.

    Args:
        area_key: 조회할 공정 Area (예: 'M14 CMP', 'M14 Photo')
    """
    data = _get_wip_status(area_key)
    tag = f"[WIP_STATUS:{area_key}]"
    group_summary = [
        {
            "group": g["group_name"],
            "wip_total": g["wip_total"],
            "running": g["wip_running"],
            "queue": g["wip_queue"],
            "move": f"{g['move_actual']}/{g['move_target']}",
            "projected": g["move_projected"],
            "achieve_pct": g["achieve_pct"],
            "down_eq": sum(1 for e in g["equipments"] if e["status"] == "DOWN"),
            "pm_eq": sum(1 for e in g["equipments"] if e["status"] == "PM"),
        }
        for g in data["process_groups"]
    ]
    result = {
        "area": data["area_name"],
        "timestamp": data["timestamp"],
        "shift_elapsed_h": data["shift_elapsed_h"],
        "shift_remaining_h": data["shift_remaining_h"],
        "total_wip": data["total_wip"],
        "move_actual": data["total_move_actual"],
        "move_target": data["total_move_target"],
        "move_projected": data["total_move_projected"],
        "achieve_pct": data["total_achieve_pct"],
        "groups": group_summary,
        "chart_tag": tag,
        "instruction": (
            f"WIP 현황을 간결하게 요약한 뒤 반드시 '{tag}' 태그를 응답에 포함하세요. "
            "태그가 있어야 WIP 대시보드가 렌더링됩니다."
        ),
    }
    return _json(result)


@tool
def get_defect_step_overlay(lot_id: str, wafer_no: int) -> str:
    """특정 Lot/Wafer에서 현재 공정 step의 defect과 이전 step들의 defect을 동일 wafer 위에
    overlay하여 비교합니다. 이전 step에서 발생한 defect이 후속 step에서 다른 유형으로
    변형되어 나타나는 carryover를 추적합니다.
    예: LITHO 단계의 PARTICLE이 ETCH 후 PIT으로, CMP 후 CLUSTER로 변형되는 경로를 확인.
    SFPT에서 볼록 형태로 보이는 defect이 어느 step부터 시작됐는지 분석할 때 사용하세요.

    Args:
        lot_id: 조회할 Lot ID
        wafer_no: Wafer 번호 (1~25)
    """
    data = _mock_defect_step_overlay(lot_id, wafer_no)
    n_carryover = len(data["carryover_clusters"])
    tag = f"[DEFECT_STEP_OVERLAY:{lot_id}:{wafer_no}]"
    result = {
        "lot_id": data["lot_id"],
        "wafer_no": data["wafer_no"],
        "current_step": data["current_step"],
        "steps_summary": [
            {"step": s["step_name"], "defect_count": s["defect_count"],
             "is_current": s["is_current"], "desc": s["step_desc"]}
            for s in data["steps"]
        ],
        "carryover_count": n_carryover,
        "chart_tag": tag,
        "instruction": (
            f"분석 결과를 요약하고 반드시 '{tag}' 태그를 응답에 포함하세요. "
            f"carryover defect {n_carryover}건이 복수 step에서 감지되었습니다. "
            "태그가 있어야 step overlay 차트가 렌더링됩니다."
        ),
    }
    return _json(result)


TOOLS = [
    get_lot_hold_info,
    get_lot_trend,
    get_wafer_map,
    get_defect_map,
    get_defect_trend,
    get_yield_defect,
    get_defect_yield_history,
    analyze_yield_grouping,
    get_daily_report,
    get_wip_status,
    get_defect_step_overlay,
]
