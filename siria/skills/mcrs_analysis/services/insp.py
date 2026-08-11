"""INSP MAP(검사 맵) 조회 비즈니스 로직.

담당 기능:
- 선택한 공정의 INSP MAP — MCRS 발생 슬롯 + 동일 Lot 의 나머지 슬롯
- 같은 Lot/슬롯이 지나온 과거 검사 공정의 MAP (이어보기)
- 같은 장비를 지나간 다른 device/공정의 검사 실적 (장비 이슈 판별용)

이미지 자체는 절대 이 계층에서 바이트로 다루지 않는다. 참조(URL)만 만들고
실제 렌더링은 호출한 쪽(가이아 UI)이 담당한다 — LLM 컨텍스트에 이미지 데이터가
들어가면 토큰이 폭발한다.
"""
from __future__ import annotations

import random
from datetime import timedelta

from core.errors import ToolError

from . import mcrs

# TODO: 가이아2.0 의 이미지 서빙 규약에 맞게 교체.
#       이미지 참조 생성은 이 함수 하나로 모아두어 규약이 바뀌어도 여기만 고치면 되게 한다.
_IMAGE_BASE = "/api/mcrs/image"


def insp_map_url(lot_id: str, step_id: str, slot_no: int) -> str:
    return f"{_IMAGE_BASE}/insp-map?lot_id={lot_id}&step_id={step_id}&slot={slot_no}"


def get_insp_map(lot_id: str, step_id: str) -> dict:
    """선택한 공정의 INSP MAP 을 Lot 의 전체 슬롯에 대해 반환한다.

    MCRS 가 발생한 슬롯만이 아니라 동일 Lot 의 다른 슬롯도 함께 돌려준다.
    한 슬롯만 튀는지, Lot 전체가 나쁜지가 원인 판별의 첫 갈림길이기 때문이다.
    """
    issue = mcrs.resolve_issue(lot_id, step_id)
    rng = random.Random(mcrs.seed(issue["issue_id"], "inspmap"))

    slots = []
    for slot_no in range(1, mcrs.SLOTS_PER_LOT + 1):
        is_target = slot_no == issue["slot_no"]
        if is_target:
            defect_count = issue["defect_count"]
        else:
            # 인접 슬롯은 조금 더 높게 — 슬롯 위치 상관성을 보기 위한 mock
            adjacency = 1.6 if abs(slot_no - issue["slot_no"]) <= 2 else 1.0
            defect_count = int(issue["defect_count"] * 0.18 * adjacency * rng.uniform(0.6, 1.4))
        slots.append(
            {
                "slot_no": slot_no,
                "defect_count": defect_count,
                "is_mcrs_slot": is_target,
                "image_url": insp_map_url(issue["lot_id"], issue["step_id"], slot_no),
            }
        )

    normal = [s["defect_count"] for s in slots if not s["is_mcrs_slot"]]
    return {
        "issue": issue,
        "slots": slots,
        "slot_count": len(slots),
        "mcrs_slot_no": issue["slot_no"],
        "normal_mean": round(sum(normal) / len(normal), 1) if normal else 0.0,
        "normal_max": max(normal) if normal else 0,
    }


def get_insp_map_history(lot_id: str, step_id: str, slot_no: int | None = None) -> dict:
    """같은 Lot/슬롯이 지나온 과거 검사 공정의 MAP 을 오래된 순으로 반환한다.

    "이 슬롯이 원래부터 나빴는지, 이 공정에서 나빠졌는지"를 보기 위한 것이다.

    slot_no 를 생략하면 MCRS 가 발생한 슬롯을 사용한다.
    """
    issue = mcrs.resolve_issue(lot_id, step_id)
    target_slot = slot_no or issue["slot_no"]
    if not 1 <= target_slot <= mcrs.SLOTS_PER_LOT:
        raise ToolError(
            f"조회 실패: 슬롯 번호는 1~{mcrs.SLOTS_PER_LOT} 범위여야 합니다 "
            f"(입력: {target_slot})."
        )

    prior = mcrs.prior_insp_steps(issue)
    rng = random.Random(mcrs.seed(issue["issue_id"], "history", target_slot))

    timeline = []
    for past in prior:
        timeline.append(
            {
                "step_id": past["step_id"],
                "step_desc": past["step_desc"],
                "eq_id": past["eq_id"],
                "inspected_at": past["detected_at"],
                "defect_count": int(past["defect_count"] * rng.uniform(0.15, 0.5)),
                "image_url": insp_map_url(issue["lot_id"], past["step_id"], target_slot),
            }
        )

    # 마지막에 현재(MCRS 발생) 공정을 붙여 증가 추이를 한 줄로 볼 수 있게 한다.
    timeline.append(
        {
            "step_id": issue["step_id"],
            "step_desc": issue["step_desc"],
            "eq_id": issue["eq_id"],
            "inspected_at": issue["detected_at"],
            "defect_count": issue["defect_count"],
            "image_url": insp_map_url(issue["lot_id"], issue["step_id"], target_slot),
            "is_mcrs_step": True,
        }
    )

    return {"issue": issue, "slot_no": target_slot, "timeline": timeline}


def get_eq_insp_coverage(lot_id: str, step_id: str, days: int = 30) -> dict:
    """MCRS 발생 장비를 지나간 '다른 device / 다른 공정' 의 검사 실적을 반환한다.

    장비 문제인지(다른 device 도 같이 나쁨) 이 device/공정 특유의 문제인지
    (이 조합만 나쁨) 를 가르는 근거가 된다.
    """
    issue = mcrs.resolve_issue(lot_id, step_id)
    if days < 1 or days > 180:
        raise ToolError("조회 실패: 조회 기간(days)은 1~180 사이여야 합니다.")

    rng = random.Random(mcrs.seed(issue["eq_id"], "coverage", days))
    detected = mcrs.parse_detected_at(issue)

    # TODO: 실제로는 장비 이력 테이블에서 기간 내 처리된 device/step 조합을 조회.
    other_devices = ["D7Y-256G", "D5X-128G", "D9Z-512G"]
    other_steps = ["INSP-CMP-01", "INSP-CMP-02"]

    rows = []
    for device_id in other_devices:
        for other_step in other_steps:
            if device_id == issue["device_id"] and other_step == issue["step_id"]:
                continue  # MCRS 가 난 조합 자신은 제외
            lot_count = rng.randint(0, 9)
            if lot_count == 0:
                continue  # 기간 내 검사 실적 없음
            mean_defect = round(issue["defect_count"] * 0.25 * rng.uniform(0.5, 1.9), 1)
            rows.append(
                {
                    "device_id": device_id,
                    "step_id": other_step,
                    "lot_count": lot_count,
                    "mean_defect": mean_defect,
                    "last_inspected_at": (
                        detected - timedelta(hours=rng.randint(2, days * 24))
                    ).strftime("%Y-%m-%d %H:%M"),
                    # 기준선 대비 2배 넘게 높으면 같이 이상한 것으로 표시
                    "abnormal": mean_defect > issue["defect_count"] * 0.5,
                }
            )

    return {
        "issue": issue,
        "days": days,
        "rows": sorted(rows, key=lambda r: r["mean_defect"], reverse=True),
        "abnormal_count": sum(1 for r in rows if r["abnormal"]),
    }
