"""REV(리뷰) 이미지 조회 — 범용 조회 계층.

지정한 슬롯의 결함 좌표별 SEM 리뷰 이미지를 반환한다. MCRS 여부와 무관하게 동작하며,
MCRS 가 없으면 슬롯 번호를 명시해야 한다 (어느 슬롯을 볼지 정할 근거가 없으므로).

핵심 요구사항: 같은 좌표에서 여러 번 찍힌 이미지는 하나로 뭉뚱그리지 않고
rev_1, rev_2, rev_3, rev_4 형태로 묶어서 돌려준다. 같은 결함을 배율/시점을 달리해
찍은 것이라 나란히 봐야 판독이 된다.
"""
from __future__ import annotations

import random

from core.errors import ToolError

from . import context, mcrs

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
    """지정한 슬롯의 결함 좌표별 REV 이미지를 반환한다.

    반환 구조는 좌표 기준으로 묶인다:
        [{coord_id, x, y, defect_type, size_um, revs: [{rev, image_url}, ...]}, ...]

    slot_no 를 생략하면 MCRS 발생 슬롯을 쓴다. MCRS 가 없으면 슬롯 지정이 필요하다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    slot = mcrs.target_slot(ctx, slot_no)
    if limit < 1:
        raise ToolError("조회 실패: limit 은 1 이상이어야 합니다.")

    issue = ctx["mcrs"]
    # 결함 수는 MCRS 가 있으면 그 값, 없으면 공정 기준선을 따른다.
    if issue and issue["slot_no"] == slot:
        defect_level = issue["defect_count"]
    else:
        defect_level = context.step_baseline(ctx)

    rng = random.Random(context.seed(ctx["lot_id"], ctx["step_id"], "review", slot))

    # TODO: 실제 결함 좌표 테이블 조회로 교체. kill 확률/크기 순 정렬이 실전 기준.
    defect_types = ["SCRATCH", "PARTICLE", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"]
    coord_total = max(1, int(defect_level * 0.08))
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
                            ctx["lot_id"], ctx["step_id"], slot, coord_id, rev
                        ),
                    }
                    for rev in range(1, rev_count + 1)
                ],
            }
        )

    return {
        "ctx": ctx,
        "slot_no": slot,
        "coord_total": coord_total,
        "coord_shown": shown,
        "coords": coords,
    }
