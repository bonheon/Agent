import random
import math
from datetime import datetime, timedelta

# 첫 lot 처리 시작일 (mock 기준점)
_BASE_DATE = datetime(2026, 4, 1, 8, 0, 0)
# lot 순서 → 날짜 오프셋 (5일 간격, 25 wafer × 6h = 6.25일 span → lot 간 약간 겹침)
_LOT_ORDER = {lot: i for i, lot in enumerate(
    ["TE2FE35", "TE2FE36", "TE2FE37", "TE2FE38", "TE2FE39", "TE2FE40", "TE2FE41", "TE2FE42"]
)}

def _wafer_ts(lot_id: str, wafer_no: int) -> int:
    """Wafer 처리 시각을 Unix timestamp(ms)로 반환."""
    lot_start = _BASE_DATE + timedelta(days=_LOT_ORDER.get(lot_id, 0) * 5)
    wafer_dt  = lot_start + timedelta(hours=(wafer_no - 1) * 6)
    return int(wafer_dt.timestamp() * 1000)  # JavaScript Date.getTime() 호환

LOTS = ["TE2FE35", "TE2FE36", "TE2FE37", "TE2FE38", "TE2FE39", "TE2FE40", "TE2FE41", "TE2FE42"]

LOT_META: dict[str, dict] = {
    "TE2FE35": {"recipe": "RECIPE_A", "equipment": "EQ_001", "process_id": "PROC_001", "custom_group": "GROUP_A"},
    "TE2FE36": {"recipe": "RECIPE_A", "equipment": "EQ_002", "process_id": "PROC_001", "custom_group": "GROUP_A"},
    "TE2FE37": {"recipe": "RECIPE_B", "equipment": "EQ_001", "process_id": "PROC_002", "custom_group": "GROUP_B"},
    "TE2FE38": {"recipe": "RECIPE_B", "equipment": "EQ_003", "process_id": "PROC_002", "custom_group": "GROUP_B"},
    "TE2FE39": {"recipe": "RECIPE_C", "equipment": "EQ_002", "process_id": "PROC_001", "custom_group": "GROUP_A"},
    "TE2FE40": {"recipe": "RECIPE_C", "equipment": "EQ_003", "process_id": "PROC_002", "custom_group": "GROUP_B"},
    "TE2FE41": {"recipe": "RECIPE_A", "equipment": "EQ_001", "process_id": "PROC_001", "custom_group": "GROUP_A"},
    "TE2FE42": {"recipe": "RECIPE_B", "equipment": "EQ_002", "process_id": "PROC_002", "custom_group": "GROUP_A"},
}

# recipe → pass rate base (%) — clear difference for analysis
_RECIPE_BASE: dict[str, dict] = {
    "RECIPE_A": {"PT1H": 95.5, "PT1H_outer": 94.2, "PT1H_center": 97.1, "PT1H_inner": 95.8},
    "RECIPE_B": {"PT1H": 92.0, "PT1H_outer": 90.5, "PT1H_center": 93.8, "PT1H_inner": 92.3},
    "RECIPE_C": {"PT1H": 88.5, "PT1H_outer": 86.9, "PT1H_center": 90.2, "PT1H_inner": 89.1},
}

# equipment → fail rate base (%) — clear difference for analysis
_EQ_BASE: dict[str, dict] = {
    "EQ_001": {"bl_lkg": 2.5, "ledic": 1.2},
    "EQ_002": {"bl_lkg": 1.8, "ledic": 0.9},
    "EQ_003": {"bl_lkg": 4.5, "ledic": 2.5},
}

PASS_PARAMS = ["PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner"]
FAIL_PARAMS = ["bl_lkg", "ledic"]

GROUPING_COLUMNS = [
    {"key": "recipe",       "label": "Recipe"},
    {"key": "equipment",    "label": "Equipment"},
    {"key": "process_id",   "label": "Process ID"},
    {"key": "custom_group", "label": "Custom Group"},
]

YIELD_PARAMS_META = [
    {"key": "PT1H",        "label": "PT1H",        "type": "pass", "unit": "%"},
    {"key": "PT1H_outer",  "label": "PT1H Outer",  "type": "pass", "unit": "%"},
    {"key": "PT1H_center", "label": "PT1H Center", "type": "pass", "unit": "%"},
    {"key": "PT1H_inner",  "label": "PT1H Inner",  "type": "pass", "unit": "%"},
    {"key": "bl_lkg",      "label": "BL Leakage",  "type": "fail", "unit": "%"},
    {"key": "ledic",       "label": "LEDIC",        "type": "fail", "unit": "%"},
]


def _generate_wafer(lot_id: str, wafer_no: int) -> dict:
    meta = LOT_META[lot_id]
    rng = random.Random(hash(f"{lot_id}-yield-{wafer_no}") % 2**31)

    row: dict = {"lot_id": lot_id, "wafer_no": wafer_no, "process_ts": _wafer_ts(lot_id, wafer_no), **meta}

    for param in PASS_PARAMS:
        base = _RECIPE_BASE[meta["recipe"]][param]
        row[param] = round(min(99.9, max(70.0, base + rng.gauss(0, 1.4))), 2)

    for param in FAIL_PARAMS:
        base = _EQ_BASE[meta["equipment"]][param]
        row[param] = round(max(0.0, base + rng.gauss(0, base * 0.22)), 2)

    return row


def _percentile(sorted_vals: list[float], pct: float) -> float:
    n = len(sorted_vals)
    idx = (n - 1) * pct / 100
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def _stats(values: list[float]) -> dict:
    n = len(values)
    if n == 0:
        return {}
    sv = sorted(values)
    mean = sum(values) / n
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / n)
    q1     = _percentile(sv, 25)
    median = _percentile(sv, 50)
    q3     = _percentile(sv, 75)
    return {
        "mean":   round(mean, 2),
        "std":    round(std, 2),
        "min":    round(sv[0], 2),
        "max":    round(sv[-1], 2),
        "count":  n,
        "q1":     round(q1, 2),
        "median": round(median, 2),
        "q3":     round(q3, 2),
        "ucl":    round(mean + 3 * std, 2),
        "lcl":    round(mean - 3 * std, 2),
    }


def get_all_lots() -> list[str]:
    return LOTS


def generate_yield_data(lot_ids: list[str]) -> list[dict]:
    rows = []
    for lot_id in lot_ids:
        if lot_id not in LOT_META:
            continue
        for wafer_no in range(1, 26):
            rows.append(_generate_wafer(lot_id, wafer_no))
    return rows


def analyze_yield(lot_ids: list[str], group_by: str, yield_params: list[str]) -> dict:
    rows = generate_yield_data(lot_ids)

    buckets: dict[str, list[dict]] = {}
    for row in rows:
        key = str(row.get(group_by, "unknown"))
        buckets.setdefault(key, []).append(row)

    groups = []
    for gval, grows in sorted(buckets.items()):
        stats = {
            p: _stats([r[p] for r in grows if p in r])
            for p in yield_params
        }
        wafers = [
            {k: r[k] for k in ["lot_id", "wafer_no", "process_ts"] + yield_params if k in r}
            for r in grows
        ]
        groups.append({
            "group_value": gval,
            "count": len(grows),
            "stats": stats,
            "wafers": wafers,
        })

    return {
        "group_by":     group_by,
        "lot_ids":      lot_ids,
        "yield_params": yield_params,
        "groups":       groups,
        "total_wafers": len(rows),
    }
