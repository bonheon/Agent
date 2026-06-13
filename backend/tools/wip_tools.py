"""
WIP (Work In Progress) 관리 Mock 데이터.
공정 Area별 WIP 현황, 장비 Status, 이동 실적/목표/예상을 제공합니다.
"""
import math
import random
from datetime import datetime

# ── 지원 Area 설정 ──────────────────────────────────────────────
AREA_CONFIG = {
    "M14 CMP": {
        "area_id":   "M14_CMP",
        "area_name": "M14 CMP Area",
        "shift_start_h": 8,
        "shift_end_h":   20,
        "process_groups": [
            {
                "group_id":   "STI-CMP",
                "group_name": "STI CMP",
                "desc":       "Shallow Trench Isolation 평탄화",
                "eq_ids":     ["CMP01A", "CMP01B", "CMP01C", "CMP01D"],
                "move_target_day": 48,
                "process_time_min": 55,
            },
            {
                "group_id":   "POLY-CMP",
                "group_name": "Poly CMP",
                "desc":       "Poly-Silicon Gate 평탄화",
                "eq_ids":     ["CMP02A", "CMP02B", "CMP02C"],
                "move_target_day": 36,
                "process_time_min": 65,
            },
            {
                "group_id":   "W-CMP",
                "group_name": "W Plug CMP",
                "desc":       "Tungsten Contact Plug 평탄화",
                "eq_ids":     ["CMP03A", "CMP03B", "CMP03C", "CMP03D"],
                "move_target_day": 52,
                "process_time_min": 48,
            },
            {
                "group_id":   "Cu-CMP1",
                "group_name": "Cu CMP 1st",
                "desc":       "1차 구리 배선 평탄화",
                "eq_ids":     ["CMP04A", "CMP04B", "CMP04C"],
                "move_target_day": 40,
                "process_time_min": 72,
            },
            {
                "group_id":   "Cu-CMP2",
                "group_name": "Cu CMP 2nd",
                "desc":       "2차 구리 배선 평탄화",
                "eq_ids":     ["CMP05A", "CMP05B"],
                "move_target_day": 24,
                "process_time_min": 68,
            },
        ],
    },
    "M14 Photo": {
        "area_id":   "M14_PHOTO",
        "area_name": "M14 Photo Area",
        "shift_start_h": 8,
        "shift_end_h":   20,
        "process_groups": [
            {
                "group_id":   "LITHO-DUV",
                "group_name": "DUV Lithography",
                "desc":       "ArF/KrF 노광 공정",
                "eq_ids":     ["SCAN01A", "SCAN01B", "SCAN02A"],
                "move_target_day": 72,
                "process_time_min": 40,
            },
            {
                "group_id":   "LITHO-EUV",
                "group_name": "EUV Lithography",
                "desc":       "EUV 노광 공정",
                "eq_ids":     ["EUV01A", "EUV01B"],
                "move_target_day": 48,
                "process_time_min": 55,
            },
            {
                "group_id":   "COAT-DEV",
                "group_name": "Coat/Dev",
                "desc":       "PR 코팅/현상",
                "eq_ids":     ["CD01A", "CD01B", "CD01C", "CD01D"],
                "move_target_day": 80,
                "process_time_min": 35,
            },
        ],
    },
}

EQ_STATUS_POOL = ["RUNNING", "RUNNING", "RUNNING", "RUNNING", "RUNNING", "RUNNING",
                  "IDLE", "IDLE", "DOWN", "PM", "SETUP"]

# 장비에 올라갈 수 있는 임시 Lot ID 목록
_WIP_LOTS = [
    "TE2FE35","TE2FE36","TE2FE37","TE2FE38","TE2FE39","TE2FE40","TE2FE41","TE2FE42",
    "TE2FE43","TE2FE44","TE2FE45","TE2FE46","TE2FE47","TE2FE48","TE2FE49","TE2FE50",
    "TE2FC10","TE2FC11","TE2FC12","TE2FC13","TE2FC14","TE2FC15","TE2FC16","TE2FC17",
]


def _now_shift_info(shift_start_h: int = 8, shift_end_h: int = 20) -> dict:
    now = datetime.now()
    shift_start = now.replace(hour=shift_start_h, minute=0, second=0, microsecond=0)
    shift_end   = now.replace(hour=shift_end_h,   minute=0, second=0, microsecond=0)
    elapsed_h   = max(0.0, min((now - shift_start).total_seconds() / 3600, shift_end_h - shift_start_h))
    remaining_h = max(0.0, (shift_end - now).total_seconds() / 3600)
    shift_total_h = shift_end_h - shift_start_h  # 12
    return {
        "now":          now,
        "shift_start":  shift_start,
        "elapsed_h":    round(elapsed_h, 2),
        "remaining_h":  round(remaining_h, 2),
        "shift_total_h": shift_total_h,
        "progress_pct": round(elapsed_h / shift_total_h * 100, 1),
    }


def _eq_status(eq_id: str, area_seed: int, process_time_min: int, shift_info: dict) -> dict:
    rng = random.Random(hash(f"{eq_id}-{datetime.now().strftime('%Y%m%d')}-{area_seed}") % 2**31)
    status = rng.choice(EQ_STATUS_POOL)

    lot_id       = None
    remaining_min = None
    run_since_min = None
    lots_today   = 0

    elapsed_h = shift_info["elapsed_h"]
    if elapsed_h > 0:
        # 오늘 처리한 lot 건수 (status 무관, 가동 가능 시간 기준)
        run_factor = {"RUNNING": 0.90, "IDLE": 0.55, "DOWN": 0.0, "PM": 0.0, "SETUP": 0.30}.get(status, 0.5)
        raw_lots = (elapsed_h * 60 / process_time_min) * run_factor
        lots_today = max(0, int(raw_lots + rng.gauss(0, 0.5)))

    util_pct = 0.0
    if shift_info["elapsed_h"] > 0 and shift_info["shift_total_h"] > 0:
        run_time_h = lots_today * process_time_min / 60
        util_pct = round(min(100.0, run_time_h / shift_info["elapsed_h"] * 100), 1)

    if status == "RUNNING":
        lot_id = rng.choice(_WIP_LOTS)
        # 현재 공정 진행 시간 (0 ~ process_time_min)
        run_since_min   = rng.randint(5, process_time_min - 5)
        remaining_min   = process_time_min - run_since_min

    return {
        "eq_id":          eq_id,
        "status":         status,
        "current_lot":    lot_id,
        "remaining_min":  remaining_min,
        "lots_today":     lots_today,
        "util_pct":       util_pct,
    }


def _group_wip(group_cfg: dict, area_seed: int, shift_info: dict) -> dict:
    rng = random.Random(hash(f"{group_cfg['group_id']}-wip-{area_seed}") % 2**31)

    eq_list = [
        _eq_status(eid, area_seed, group_cfg["process_time_min"], shift_info)
        for eid in group_cfg["eq_ids"]
    ]

    n_running = sum(1 for e in eq_list if e["status"] == "RUNNING")
    n_queue   = rng.randint(max(0, 4 - n_running), 16)
    n_total   = n_running + n_queue

    # 이동 실적: 오늘 장비들의 합계 + 시간 비례 진척
    move_actual_raw = sum(e["lots_today"] for e in eq_list)
    move_actual = max(0, move_actual_raw + rng.randint(-1, 1))

    target = group_cfg["move_target_day"]
    elapsed_h = shift_info["elapsed_h"]
    remaining_h = shift_info["remaining_h"]

    # 예상 이동: 현재 속도 × 잔여 시간
    if elapsed_h > 0.5:
        rate_per_h = move_actual / elapsed_h
        move_projected = round(move_actual + rate_per_h * remaining_h)
    else:
        move_projected = round(target * 0.8)

    achieve_pct = round(move_projected / target * 100, 1) if target > 0 else 0.0

    return {
        "group_id":       group_cfg["group_id"],
        "group_name":     group_cfg["group_name"],
        "desc":           group_cfg["desc"],
        "wip_running":    n_running,
        "wip_queue":      n_queue,
        "wip_total":      n_total,
        "move_target":    target,
        "move_actual":    move_actual,
        "move_projected": move_projected,
        "achieve_pct":    achieve_pct,
        "process_time_min": group_cfg["process_time_min"],
        "equipments":     eq_list,
    }


def get_wip_status(area_key: str) -> dict:
    """area_key: 'M14 CMP', 'M14 Photo' 등"""
    # 대소문자 및 공백 유연하게 매칭
    matched = None
    key_norm = area_key.strip().upper()
    for k, v in AREA_CONFIG.items():
        if k.upper() in key_norm or key_norm in k.upper():
            matched = (k, v)
            break
    if matched is None:
        # fallback: M14 CMP
        matched = ("M14 CMP", AREA_CONFIG["M14 CMP"])

    cfg = matched[1]
    shift_info = _now_shift_info(cfg["shift_start_h"], cfg["shift_end_h"])
    area_seed  = hash(f"{matched[0]}-{datetime.now().strftime('%Y%m%d')}") % 2**31

    groups = [
        _group_wip(g, area_seed, shift_info)
        for g in cfg["process_groups"]
    ]

    total_wip      = sum(g["wip_total"]      for g in groups)
    total_target   = sum(g["move_target"]    for g in groups)
    total_actual   = sum(g["move_actual"]    for g in groups)
    total_projected = sum(g["move_projected"] for g in groups)
    total_achieve_pct = round(total_projected / total_target * 100, 1) if total_target > 0 else 0.0

    now = shift_info["now"]
    return {
        "area_key":          matched[0],
        "area_name":         cfg["area_name"],
        "timestamp":         now.strftime("%Y-%m-%d %H:%M"),
        "shift_elapsed_h":   shift_info["elapsed_h"],
        "shift_remaining_h": shift_info["remaining_h"],
        "shift_progress_pct": shift_info["progress_pct"],
        "total_wip":         total_wip,
        "total_move_target": total_target,
        "total_move_actual": total_actual,
        "total_move_projected": total_projected,
        "total_achieve_pct": total_achieve_pct,
        "process_groups":    groups,
    }


def list_supported_areas() -> list[str]:
    return list(AREA_CONFIG.keys())
