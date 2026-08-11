"""REV(리뷰) 이미지 조회 비즈니스 로직.

MCRS 가 발생한 슬롯의 결함 좌표별 SEM 리뷰 이미지를 반환한다.

핵심 요구사항: 같은 좌표에서 여러 번 찍힌 이미지는 하나로 뭉뚱그리지 않고
rev_1, rev_2, rev_3, rev_4 형태로 묶어서 돌려준다. 같은 결함을 배율/시점을 달리해
찍은 것이라 나란히 봐야 판독이 되기 때문이다.
"""
from __future__ import annotations

import random

from core.errors import ToolError

from . import mcrs

# TODO: 가이아2.0 이미지 서빙 규약에 맞게 교체 (insp._IMAGE_BASE 와 동일 규약).
_IMAGE_BASE = "/api/mcrs/image"

# 좌표 하나당 리뷰 이미지 최대 장수 (rev_1 ~ rev_4)
MAX_REV_PER_COORD = 4

# 한 번에 돌려줄 좌표 수 상한 — 결함이 수백 개일 때 응답이 터지는 것을 막는다.
DEFAULT_COORD_LIMIT = 10


def review_image_url(lot_id: str, step_id: str, slot_no: int, coord_id: str, rev: int) -> str:
    return (
        f"{_IMAGE_BASE}/review?lot_id={lot_id}&step_id={step_id}"
        f"&slot={slot_no}&coord={coord_id}&rev={rev}"
    )


def get_review_images(
    lot_id: str,
    step_id: str,
    slot_no: int | None = None,
    limit: int = DEFAULT_COORD_LIMIT,
) -> dict:
    """MCRS 발생 슬롯의 결함 좌표별 REV 이미지를 반환한다.

    반환 구조는 좌표 기준으로 묶인다:
        [{coord_id, x, y, defect_type, size_um, revs: [{rev, image_url}, ...]}, ...]

    slot_no 를 생략하면 MCRS 가 발생한 슬롯을 사용한다.
    """
    issue = mcrs.resolve_issue(lot_id, step_id)
    target_slot = slot_no or issue["slot_no"]

    if not 1 <= target_slot <= mcrs.SLOTS_PER_LOT:
        raise ToolError(
            f"조회 실패: 슬롯 번호는 1~{mcrs.SLOTS_PER_LOT} 범위여야 합니다 "
            f"(입력: {target_slot})."
        )
    if limit < 1:
        raise ToolError("조회 실패: limit 은 1 이상이어야 합니다.")

    rng = random.Random(mcrs.seed(issue["issue_id"], "review", target_slot))

    # TODO: 실제 결함 좌표 테이블 조회로 교체. kill 확률/크기 순 정렬이 실전 기준.
    defect_types = ["SCRATCH", "PARTICLE", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"]
    coord_total = max(1, int(issue["defect_count"] * 0.08))
    shown = min(coord_total, limit)

    coords = []
    for idx in range(shown):
        coord_id = f"C-{idx + 1:03d}"
        rev_count = rng.randint(1, MAX_REV_PER_COORD)
        coords.append(
            {
                "coord_id": coord_id,
                "x": round(rng.uniform(-150.0, 150.0), 1),
                "y": round(rng.uniform(-150.0, 150.0), 1),
                "defect_type": rng.choice(defect_types),
                "size_um": round(rng.uniform(0.2, 4.5), 2),
                "revs": [
                    {
                        "rev": rev,
                        "image_url": review_image_url(
                            issue["lot_id"], issue["step_id"], target_slot, coord_id, rev
                        ),
                    }
                    for rev in range(1, rev_count + 1)
                ],
            }
        )

    return {
        "issue": issue,
        "slot_no": target_slot,
        "coord_total": coord_total,
        "coord_shown": shown,
        "coords": coords,
    }
