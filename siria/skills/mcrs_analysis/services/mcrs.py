"""MCRS 이슈 조회 — 공정 이력 위에 얹히는 보강 계층.

장비·device·처리시각은 여기서 만들지 않는다. 그건 `context.py` (공정 이력) 담당이고,
이 모듈은 "그 공정에서 MCRS 가 났는가, 났다면 어느 슬롯에 몇 개인가" 만 더한다.

`resolve()` 가 두 계층을 합쳐주는 단일 진입점이다. 조회 tool 은 전부 이걸 쓰며,
MCRS 가 없으면 `ctx["mcrs"] is None` 인 컨텍스트를 그대로 돌려받는다 — 실패하지 않는다.
"""
from __future__ import annotations

from core.errors import ToolError

from . import context

# TODO: mock 제거하고 실제 MCRS 이슈 테이블 조회로 교체.
#       lot_id → {step_id: 이슈}. 장비/device/시각은 공정 이력에서 합쳐진다.
_MOCK_ISSUES: dict[str, dict[str, dict]] = {
    "TE2FE35": {
        "INSP-CMP-01": {
            "issue_id": "MC-20260810-001",
            "slot_no": 12,
            "defect_count": 142,
            "mcrs_code": "MCRS-SCRATCH",
        },
        "INSP-ETCH-03": {
            "issue_id": "MC-20260810-002",
            "slot_no": 7,
            "defect_count": 61,
            "mcrs_code": "MCRS-PARTICLE",
        },
        "INSP-PHOTO-02": {
            "issue_id": "MC-20260810-003",
            "slot_no": 12,
            "defect_count": 33,
            "mcrs_code": "MCRS-RESIDUE",
        },
    },
    "TE2FE36": {
        "INSP-CMP-01": {
            "issue_id": "MC-20260811-001",
            "slot_no": 3,
            "defect_count": 97,
            "mcrs_code": "MCRS-SCRATCH",
        },
    },
}


def resolve(lot_id: str, step_id: str) -> dict:
    """공정 이력 컨텍스트에 MCRS 이슈를 보강해서 반환한다.

    MCRS 가 없어도 실패하지 않는다. 그 경우 ctx["mcrs"] 가 None 이다.
    조회 tool 은 전부 이 함수를 통해 컨텍스트를 얻는다.
    """
    ctx = context.resolve_context(lot_id, step_id)
    issue = _MOCK_ISSUES.get(ctx["lot_id"], {}).get(ctx["step_id"])
    if issue:
        ctx["mcrs"] = {**issue, "detected_at": ctx["processed_at"]}
    return ctx


def get_mcrs_issues(lot_id: str) -> list[dict]:
    """Lot 1개에서 발생한 MCRS 이슈 목록을 발생 시각 내림차순으로 반환한다.

    이슈가 없으면 빈 리스트를 반환한다 — "MCRS 없음" 은 실패가 아니라 유효한 답이다.
    """
    route = context.get_route(lot_id)  # Lot 자체가 없으면 여기서 ToolError
    issues_by_step = _MOCK_ISSUES.get(context.normalize_lot_id(lot_id), {})

    issues = [
        {**step, **issues_by_step[step["step_id"]], "detected_at": step["processed_at"]}
        for step in route
        if step["step_id"] in issues_by_step
    ]
    return sorted(issues, key=lambda i: i["detected_at"], reverse=True)


def require_mcrs(ctx: dict) -> dict:
    """MCRS 이슈가 반드시 있어야 하는 분석 계층 tool 이 쓰는 가드.

    조회 계층은 이걸 쓰지 않는다 — MCRS 없이도 동작해야 하기 때문이다.
    """
    if ctx["mcrs"]:
        return ctx["mcrs"]
    raise ToolError(
        f"조회 실패: '{ctx['lot_id']}' 의 공정 '{ctx['step_id']}' 에는 MCRS 이슈가 "
        "없어 이 분석을 할 수 없습니다. 이 공정의 일반 데이터만 필요하면 조회 tool"
        "(get_insp_map, get_step_trend 등)을 사용하세요."
    )


def target_slot(ctx: dict, slot_no: int | None) -> int:
    """분석 대상 슬롯을 정한다.

    명시하면 그 슬롯, 생략하면 MCRS 발생 슬롯. MCRS 도 없고 지정도 없으면
    어느 슬롯인지 알 수 없으므로 사용자에게 되묻게 한다.
    """
    if slot_no is None:
        if ctx["mcrs"]:
            return ctx["mcrs"]["slot_no"]
        raise ToolError(
            f"조회 실패: '{ctx['lot_id']}' 의 공정 '{ctx['step_id']}' 에는 MCRS 이슈가 "
            "없어 대상 슬롯을 자동으로 정할 수 없습니다. "
            f"사용자에게 슬롯 번호(1~{ctx['slot_count']})를 물어보세요."
        )
    if not 1 <= slot_no <= ctx["slot_count"]:
        raise ToolError(
            f"조회 실패: 슬롯 번호는 1~{ctx['slot_count']} 범위여야 합니다 (입력: {slot_no})."
        )
    return slot_no
