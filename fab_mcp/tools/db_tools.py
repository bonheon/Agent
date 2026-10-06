"""
DB 조회용 Mock 데이터 생성기 모음. LangChain tool 정의는 tools/langgraph_tools.py에 있습니다.
실제 Oracle 연결 전까지는 Mock 데이터를 반환합니다.
"""
import base64
import math
import random
import re
from datetime import datetime, timedelta

METRIC_BASES = {
    "thickness":      1000.0,   # Å
    "cd":               28.0,   # nm
    "particle_count":   15.0,   # count
}
METRIC_SIGMA = {
    "thickness":  8.0,
    "cd":         0.5,
    "particle_count": 3.0,
}


# ── Lot ID 파싱 ───────────────────────────────────────────────
def _parse_lot(lot_id: str):
    m = re.search(r"(\d+)$", lot_id)
    if m:
        return lot_id[: m.start()], int(m.group(1))
    return lot_id, 1


# ── Hold 정보 ─────────────────────────────────────────────────
def _mock_lot_hold_info(lot_id: str) -> dict:
    random.seed(hash(lot_id) % 2**31)
    reasons = [
        {"code": "PARTICLE_DEFECT",  "desc": "파티클 결함 - 리소그래피 공정 후 검사 기준 초과"},
        {"code": "CD_OOC",           "desc": "CD(Critical Dimension) 규격 이탈 - 에칭 조건 점검 필요"},
        {"code": "THICKNESS_OOC",    "desc": "박막 두께 규격 이탈 - CVD 조건 점검 필요"},
    ]
    reason = random.choice(reasons)
    return {
        "lot_id": lot_id,
        "status": "HOLD",
        "hold_reason_code": reason["code"],
        "hold_reason_desc": reason["desc"],
        "hold_time": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
        "process_step": f"STEP_{random.randint(10, 90):02d}",
        "equipment_id": f"EQ{random.randint(100, 999)}",
        "responsible_engineer": "Mock Data - DB 연결 후 실제 담당자 표시",
    }


# ── Trend: 1000포인트 (40 lots × 25 slots) ───────────────────
def _mock_lot_trend_full(lot_id: str, metric: str) -> dict:
    """차트 엔드포인트용 — 1000포인트 ScatterPlot + UCL/LCL + OOC 목록"""
    rng = random.Random(hash(lot_id + metric) % 2**31)
    prefix, num = _parse_lot(lot_id)

    base  = METRIC_BASES.get(metric, 100.0)
    sigma = METRIC_SIGMA.get(metric, base * 0.008)

    start = max(1, num - 19)  # 40개 로트 중 기준 Lot이 중앙 부근
    points = []
    idx = 0

    for lot_i in range(40):
        l_id = f"{prefix}{start + lot_i:02d}"
        lot_drift  = lot_i * sigma * 0.04          # 로트별 완만한 드리프트
        lot_offset = rng.gauss(0, sigma * 0.4)     # 로트 간 편차

        for slot in range(1, 26):
            noise = rng.gauss(0, sigma)
            value = base + lot_drift + lot_offset + noise

            # 가끔 공정 이상 spike (~2%)
            if rng.random() < 0.02:
                value += rng.choice([-1, 1]) * sigma * 3.5

            points.append({
                "lot_id": l_id,
                "slot":   slot,
                "metric": metric,
                "value":  round(value, 2),
                "index":  idx,
                "timestamp": (datetime.now() - timedelta(minutes=(1000 - idx) * 30)).isoformat(),
            })
            idx += 1

    values = [p["value"] for p in points]
    avg = sum(values) / len(values)
    std = math.sqrt(sum((v - avg) ** 2 for v in values) / len(values))
    ucl = avg + 3 * std
    lcl = avg - 3 * std

    ooc = []
    for p in points:
        p["ooc"] = p["value"] > ucl or p["value"] < lcl
        if p["ooc"]:
            ooc.append(p)

    return {
        "points": points,
        "avg":    round(avg, 2),
        "ucl":    round(ucl, 2),
        "lcl":    round(lcl, 2),
        "ooc":    ooc,
    }


def _mock_lot_trend_summary(lot_id: str, metric: str) -> dict:
    """OpenAI tool 응답용 — OOC 요약 + 차트 태그"""
    full  = _mock_lot_trend_full(lot_id, metric)
    total = len(full["points"])

    # OOC를 로트별로 그룹화
    by_lot: dict = {}
    for p in full["ooc"]:
        by_lot.setdefault(p["lot_id"], []).append(p["slot"])

    return {
        "lot_id":          lot_id,
        "metric":          metric,
        "total_points":    total,
        "avg":             full["avg"],
        "ucl":             full["ucl"],
        "lcl":             full["lcl"],
        "ooc_count":       len(full["ooc"]),
        "ooc_rate_pct":    round(len(full["ooc"]) / total * 100, 1),
        "ooc_by_lot":      {k: v for k, v in list(by_lot.items())[:6]},
        "chart_tag":       f"[TREND_CHART:{lot_id}:{metric}]",
        "follow_up_instruction": (
            "OOC 슬롯 정보를 표로 요약해서 보여주고, "
            "응답 마지막에 반드시 '해당 OOC Slot들의 Wafer Map도 확인하시겠어요?' 라고 물어보세요."
        ),
    }


# ── Wafer Map: 원형, die별 두께 ───────────────────────────────
def _mock_wafer_map(lot_id: str) -> dict:
    """차트 엔드포인트용 — 원형 20×20 격자, die별 두께(Å)"""
    grid   = 20
    center = (grid - 1) / 2   # 9.5
    nominal = 1000.0

    wafers = []
    for w in range(1, 26):
        rng = random.Random(hash(f"{lot_id}-{w}") % 2**31)
        wafer_offset = rng.gauss(0, 5)
        dies = []
        for row in range(grid):
            for col in range(grid):
                dist = math.sqrt((row - center) ** 2 + (col - center) ** 2)
                if dist > center + 0.5:
                    continue
                radial    = 20.0 * (1 - dist / center)
                noise     = rng.gauss(0, 6)
                thickness = round(nominal + radial + noise + wafer_offset, 1)
                dies.append({"row": row, "col": col, "thickness": thickness})
        avg_t = round(sum(d["thickness"] for d in dies) / len(dies), 1)
        wafers.append({"wafer_no": w, "dies": dies, "avg_thickness": avg_t})

    return {"lot_id": lot_id, "wafers": wafers, "grid_size": grid}


def _mock_wafer_map_summary(lot_id: str) -> dict:
    """OpenAI tool 응답용 — 요약 통계 + 차트 태그"""
    full        = _mock_wafer_map(lot_id)
    thicknesses = [w["avg_thickness"] for w in full["wafers"]]
    avg         = round(sum(thicknesses) / len(thicknesses), 1)
    thin_wafers = [w["wafer_no"] for w in full["wafers"] if w["avg_thickness"] < avg - 8]
    return {
        "lot_id":                  lot_id,
        "wafer_count":             len(full["wafers"]),
        "avg_thickness_angstrom":  avg,
        "min_thickness_angstrom":  round(min(thicknesses), 1),
        "max_thickness_angstrom":  round(max(thicknesses), 1),
        "thin_wafers":             thin_wafers,
        "chart_tag":               f"[WAFER_MAP:{lot_id}]",
        "note": "차트 태그를 응답에 포함하면 프론트엔드에서 Wafer Map이 렌더링됩니다.",
    }


# ── Defect ────────────────────────────────────────────────────
DEFECT_TYPES   = ["PARTICLE", "SCRATCH", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"]
DEFECT_WEIGHTS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]
KILL_PROB_ADD  = {"PARTICLE": 0.20, "SCRATCH": 0.15, "BRIDGE": 0.35,
                  "PIT": 0.10,  "RESIDUE": 0.25, "CLUSTER": 0.40}
BASE_FAIL_RATE = 0.05

# ── Step Overlay ───────────────────────────────────────────────
_PROCESS_STEPS = [
    {"step_name": "LITHO-01",  "step_order": 1, "desc": "리소그래피 패터닝 후 검사"},
    {"step_name": "ETCH-01",   "step_order": 2, "desc": "건식 식각 후 검사"},
    {"step_name": "CMP-01",    "step_order": 3, "desc": "CMP 평탄화 후 검사"},
    {"step_name": "INSP-01",   "step_order": 4, "desc": "인라인 최종 검사 (현재 STEP)"},
]

# 각 step별 defect 유형 분포 (공정 특성 반영)
_STEP_DEFECT_WEIGHTS = {
    "LITHO-01": [0.40, 0.25, 0.08, 0.03, 0.20, 0.04],  # PARTICLE, SCRATCH 위주
    "ETCH-01":  [0.15, 0.15, 0.35, 0.25, 0.05, 0.05],  # BRIDGE, PIT 위주
    "CMP-01":   [0.30, 0.30, 0.05, 0.10, 0.20, 0.05],  # PARTICLE, SCRATCH, RESIDUE
    "INSP-01":  [0.35, 0.20, 0.15, 0.15, 0.10, 0.05],  # 혼합
}

# Defect 유형 변형 맵: 이전 step에서 다음 step으로 carryover될 때 type이 바뀌는 경우
# 예: SFPT의 PARTICLE이 후속 ETCH에서 PIT이나 CLUSTER로 보일 수 있음
_CARRYOVER_TRANSFORM = {
    "PARTICLE": ["PIT", "CLUSTER", "PARTICLE"],
    "SCRATCH":  ["SCRATCH", "BRIDGE"],
    "RESIDUE":  ["BRIDGE", "PIT"],
    "BRIDGE":   ["BRIDGE", "CLUSTER"],
    "PIT":      ["PIT", "CLUSTER"],
    "CLUSTER":  ["CLUSTER", "PARTICLE"],
}


def _mock_defect_step_overlay(lot_id: str, wafer_no: int) -> dict:
    """공정 step별 defect을 overlay 비교 — carryover defect 추적 포함."""
    rng = random.Random(hash(f"{lot_id}-overlay-{wafer_no}") % 2**31)

    # carryover될 "씨앗" 위치 생성 (여러 step에 걸쳐 동일 위치 근방에 나타남)
    n_seeds = rng.randint(10, 18)
    seeds = []
    for i in range(n_seeds):
        angle  = rng.uniform(0, 2 * math.pi)
        radius = math.sqrt(rng.uniform(0, 0.88))
        seeds.append({
            "cluster_id":   f"CL{i+1:03d}",
            "x_base":       round(radius * math.cos(angle), 4),
            "y_base":       round(radius * math.sin(angle), 4),
            "start_step":   rng.randint(1, 3),
            "initial_type": rng.choices(DEFECT_TYPES, weights=DEFECT_WEIGHTS)[0],
        })

    all_steps = []
    cluster_map: dict = {}  # cluster_id -> appearances dict

    for step_info in _PROCESS_STEPS:
        sname  = step_info["step_name"]
        sorder = step_info["step_order"]
        is_cur = sorder == len(_PROCESS_STEPS)
        srng   = random.Random(hash(f"{lot_id}-{sname}-{wafer_no}") % 2**31)

        defects = []

        # ── carryover defects ─────────────────────────────────
        for seed in seeds:
            if seed["start_step"] > sorder:
                continue
            steps_elapsed = sorder - seed["start_step"]
            # 누적 jitter: step이 지날수록 위치가 조금씩 이동
            x = seed["x_base"] + srng.gauss(0, 0.012) * (steps_elapsed + 1)
            y = seed["y_base"] + srng.gauss(0, 0.012) * (steps_elapsed + 1)
            # wafer 반경 내 클리핑
            r2 = x * x + y * y
            if r2 > 0.93:
                scale = math.sqrt(0.93 / r2)
                x, y = x * scale, y * scale
            x, y = round(x, 4), round(y, 4)

            # type 변형: step이 지날수록 다른 type으로 변형될 수 있음
            if steps_elapsed == 0:
                dtype = seed["initial_type"]
            else:
                dtype = srng.choice(_CARRYOVER_TRANSFORM.get(seed["initial_type"], ["PARTICLE"]))

            size    = round(min(max(srng.lognormvariate(0, 0.5), 0.15), 6.0), 2)
            die_col = max(0, min(19, int((x + 1) / 2 * 20)))
            die_row = max(0, min(19, int((-y + 1) / 2 * 20)))
            did     = f"{sname}_{seed['cluster_id']}"

            defects.append({
                "defect_id":   did,
                "x_norm":      x, "y_norm": y,
                "die_row":     die_row, "die_col": die_col,
                "defect_type": dtype,
                "size_um":     size,
                "carryover_id": seed["cluster_id"],
            })

            if seed["cluster_id"] not in cluster_map:
                cluster_map[seed["cluster_id"]] = {
                    "cluster_id": seed["cluster_id"],
                    "x_center":  round(seed["x_base"], 4),
                    "y_center":  round(seed["y_base"], 4),
                    "appearances": {},
                }
            cluster_map[seed["cluster_id"]]["appearances"][sname] = {
                "defect_id":   did,
                "defect_type": dtype,
            }

        # ── step 고유 랜덤 defect ──────────────────────────────
        weights = _STEP_DEFECT_WEIGHTS[sname]
        n_rand  = srng.randint(8, 18)
        for i in range(n_rand):
            angle  = srng.uniform(0, 2 * math.pi)
            radius = math.sqrt(srng.uniform(0, 0.94))
            x = round(radius * math.cos(angle), 4)
            y = round(radius * math.sin(angle), 4)
            dtype   = srng.choices(DEFECT_TYPES, weights=weights)[0]
            size    = round(min(max(srng.lognormvariate(0, 0.6), 0.1), 8.0), 2)
            die_col = max(0, min(19, int((x + 1) / 2 * 20)))
            die_row = max(0, min(19, int((-y + 1) / 2 * 20)))
            defects.append({
                "defect_id":   f"{sname}_D{i+1:03d}",
                "x_norm": x, "y_norm": y,
                "die_row": die_row, "die_col": die_col,
                "defect_type": dtype,
                "size_um": size,
                "carryover_id": None,
            })

        type_counts: dict = {}
        for d in defects:
            type_counts[d["defect_type"]] = type_counts.get(d["defect_type"], 0) + 1

        all_steps.append({
            "step_name":    sname,
            "step_order":   sorder,
            "step_desc":    step_info["desc"],
            "is_current":   is_cur,
            "defect_count": len(defects),
            "type_counts":  type_counts,
            "defects":      defects,
        })

    # 2개 이상 step에 걸쳐 나타나는 carryover만 포함
    multi_clusters = [
        v for v in cluster_map.values()
        if len(v["appearances"]) >= 2
    ]

    return {
        "lot_id":             lot_id,
        "wafer_no":           wafer_no,
        "current_step":       _PROCESS_STEPS[-1]["step_name"],
        "steps":              all_steps,
        "carryover_clusters": multi_clusters,
    }


def _review_svg(defect_type: str, size_um: float, defect_id: str) -> str:
    r = min(max(int(size_um * 8), 8), 35)
    features = {
        "PARTICLE": (
            f'<circle cx="100" cy="100" r="{int(r*1.4)}" fill="#1e2035" opacity="0.8"/>'
            f'<circle cx="100" cy="100" r="{r}" fill="#e8d840" opacity="0.92"/>'
            f'<circle cx="{100-r//3}" cy="{100-r//3}" r="{max(r//3,3)}" fill="#fffac0" opacity="0.65"/>'
        ),
        "SCRATCH": (
            f'<line x1="30" y1="110" x2="170" y2="90" stroke="#d4d4d4" stroke-width="{max(r//5,2)}" stroke-linecap="round"/>'
            f'<line x1="30" y1="113" x2="170" y2="93" stroke="#707070" stroke-width="{max(r//8,1)}" opacity="0.4" stroke-linecap="round"/>'
        ),
        "BRIDGE": (
            f'<rect x="50" y="78" width="28" height="44" fill="#888" rx="2" opacity="0.7"/>'
            f'<rect x="122" y="78" width="28" height="44" fill="#888" rx="2" opacity="0.7"/>'
            f'<rect x="78" y="{100-max(r//5,3)}" width="44" height="{max(r//2,6)}" fill="#d4d000" rx="1" opacity="0.9"/>'
        ),
        "PIT": (
            f'<circle cx="100" cy="100" r="{int(r*1.3)}" fill="#18182a"/>'
            f'<circle cx="100" cy="100" r="{r}" fill="#0a0a18"/>'
            f'<circle cx="{100+r//3}" cy="{100-r//3}" r="{max(r//4,3)}" fill="#3a3a80" opacity="0.6"/>'
        ),
        "RESIDUE": (
            f'<ellipse cx="97" cy="104" rx="{int(r*1.1)}" ry="{int(r*0.7)}" fill="#9a9030" opacity="0.75" transform="rotate(-25 97 104)"/>'
            f'<ellipse cx="109" cy="96" rx="{int(r*0.75)}" ry="{int(r*0.45)}" fill="#c0b020" opacity="0.55" transform="rotate(15 109 96)"/>'
        ),
        "CLUSTER": "".join(
            f'<circle cx="{100+(i%3-1)*14}" cy="{100+(i//3)*12-6}" r="{max(r//4,3)}" fill="#f59e0b" opacity="0.88"/>'
            for i in range(6)
        ),
    }
    feat = features.get(defect_type, features["PARTICLE"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        f'<rect width="200" height="200" fill="#101820"/>'
        f'<line x1="0" y1="100" x2="200" y2="100" stroke="#1e2a38" stroke-width="0.5"/>'
        f'<line x1="100" y1="0" x2="100" y2="200" stroke="#1e2a38" stroke-width="0.5"/>'
        f'<circle cx="100" cy="100" r="62" fill="none" stroke="#1e2a38" stroke-width="0.5"/>'
        f'{feat}'
        f'<line x1="15" y1="182" x2="65" y2="182" stroke="#445566" stroke-width="1.5"/>'
        f'<line x1="15" y1="178" x2="15" y2="186" stroke="#445566" stroke-width="1"/>'
        f'<line x1="65" y1="178" x2="65" y2="186" stroke="#445566" stroke-width="1"/>'
        f'<text x="40" y="194" fill="#445566" font-size="8" text-anchor="middle" font-family="monospace">1.0 μm</text>'
        f'<text x="100" y="14" fill="#4a5a6a" font-size="8" text-anchor="middle" font-family="monospace">{defect_type} | {defect_id}</text>'
        f'</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _mock_defect_map(lot_id: str, wafer_no: int) -> dict:
    rng = random.Random(hash(f"{lot_id}-def-{wafer_no}") % 2**31)
    n   = rng.randint(20, 50)
    defects = []
    for i in range(n):
        angle  = rng.uniform(0, 2 * math.pi)
        radius = math.sqrt(rng.uniform(0, 0.94))
        x_norm = round(radius * math.cos(angle), 4)
        y_norm = round(radius * math.sin(angle), 4)
        dtype  = rng.choices(DEFECT_TYPES, weights=DEFECT_WEIGHTS)[0]
        size   = round(min(max(rng.lognormvariate(0, 0.6), 0.1), 8.0), 2)
        die_col = max(0, min(19, int((x_norm + 1) / 2 * 20)))
        die_row = max(0, min(19, int((-y_norm + 1) / 2 * 20)))
        defects.append({
            "defect_id":   f"D{i+1:03d}",
            "x_norm":      x_norm,
            "y_norm":      y_norm,
            "die_row":     die_row,
            "die_col":     die_col,
            "defect_type": dtype,
            "size_um":     size,
        })
    type_counts: dict = {}
    for d in defects:
        type_counts[d["defect_type"]] = type_counts.get(d["defect_type"], 0) + 1
    return {"lot_id": lot_id, "wafer_no": wafer_no, "defects": defects, "type_counts": type_counts}


def _mock_defect_review(lot_id: str, wafer_no: int, defect_id: str) -> dict:
    dm     = _mock_defect_map(lot_id, wafer_no)
    defect = next((d for d in dm["defects"] if d["defect_id"] == defect_id), None)
    if not defect:
        return {"error": f"{defect_id} not found"}
    return {
        **defect,
        "lot_id":       lot_id,
        "wafer_no":     wafer_no,
        "x_mm":         round(defect["x_norm"] * 148, 2),
        "y_mm":         round(defect["y_norm"] * 148, 2),
        "review_image": _review_svg(defect["defect_type"], defect["size_um"], defect_id),
    }


def _mock_defect_trend_full(lot_id: str, defect_type: str) -> dict:
    prefix, num = _parse_lot(lot_id)
    rng   = random.Random(hash(f"{lot_id}-dtrend-{defect_type}") % 2**31)
    start = max(1, num - 19)
    points = []
    for lot_i in range(40):
        l_id       = f"{prefix}{start + lot_i:02d}"
        base_count = rng.randint(5, 20)
        if rng.random() < 0.08:
            base_count += rng.randint(15, 40)
        for slot in range(1, 26):
            count = max(0, base_count + rng.randint(-3, 3))
            points.append({
                "lot_id":      l_id,
                "slot":        slot,
                "metric":      defect_type,
                "value":       count,
                "index":       len(points),
                "timestamp":   (datetime.now() - timedelta(minutes=(1000-len(points))*30)).isoformat(),
            })
    counts = [p["value"] for p in points]
    avg    = sum(counts) / len(counts)
    std    = math.sqrt(sum((c - avg)**2 for c in counts) / len(counts))
    ucl    = avg + 3 * std
    ooc    = []
    for p in points:
        p["ooc"] = p["value"] > ucl
        if p["ooc"]:
            ooc.append(p)
    return {"points": points, "avg": round(avg, 2), "ucl": round(ucl, 2), "lcl": 0, "ooc": ooc}


def _mock_yield_defect(lot_id: str, wafer_no: int) -> dict:
    dm      = _mock_defect_map(lot_id, wafer_no)
    defects = dm["defects"]
    by_die: dict = {}
    for d in defects:
        by_die.setdefault((d["die_row"], d["die_col"]), []).append(d)
    rng    = random.Random(hash(f"{lot_id}-yd-{wafer_no}") % 2**31)
    grid   = 20
    center = (grid - 1) / 2
    dies   = []
    for row in range(grid):
        for col in range(grid):
            if math.sqrt((row-center)**2 + (col-center)**2) > center + 0.5:
                continue
            local = by_die.get((row, col), [])
            fail_p = BASE_FAIL_RATE
            for d in local:
                fail_p = min(0.95, fail_p + KILL_PROB_ADD.get(d["defect_type"], 0.1))
            failed = rng.random() < fail_p
            dies.append({
                "row":          row, "col": col,
                "bin":          rng.choice([2,3,4]) if failed else 1,
                "pass":         not failed,
                "defect_count": len(local),
                "defect_types": list({d["defect_type"] for d in local}),
            })
    kill: list = []
    for dt in DEFECT_TYPES:
        affected = [d for d in dies if dt in d["defect_types"]]
        if not affected:
            continue
        killed = sum(1 for d in affected if not d["pass"])
        kill.append({
            "defect_type":    dt,
            "dies_affected":  len(affected),
            "killed_dies":    killed,
            "kill_rate_pct":  round(killed / len(affected) * 100, 1),
        })
    total   = len(dies)
    passing = sum(1 for d in dies if d["pass"])
    return {
        "lot_id":        lot_id, "wafer_no": wafer_no,
        "dies":          dies,   "grid_size": grid,
        "defects":       defects,
        "total_dies":    total,  "passing_dies": passing,
        "wafer_yield_pct": round(passing / total * 100, 1),
        "kill_analysis": kill,
    }


def _mock_defect_yield_history(lot_id: str, defect_type: str) -> dict:
    """Lot 내 전체 wafer에 대해 특정 defect 유형의 발생 건수 vs 수율 상관 분석.
    top_wafers: defect 건수 상위 10개 wafer의 die bin + defect 위치 포함."""
    all_raw = []
    for wafer_no in range(1, 26):
        dm  = _mock_defect_map(lot_id, wafer_no)
        yd  = _mock_yield_defect(lot_id, wafer_no)
        count    = dm["type_counts"].get(defect_type, 0)
        kill_row = next((k for k in yd["kill_analysis"] if k["defect_type"] == defect_type), None)
        all_raw.append({
            "wafer_no":      wafer_no,
            "defect_count":  count,
            "yield_pct":     yd["wafer_yield_pct"],
            "kill_rate_pct": kill_row["kill_rate_pct"] if kill_row else 0.0,
            "killed_dies":   kill_row["killed_dies"]   if kill_row else 0,
            "dies_affected": kill_row["dies_affected"] if kill_row else 0,
            "_dies":         yd["dies"],
            "_defects":      [d for d in dm["defects"] if d["defect_type"] == defect_type],
        })

    # summary list (no heavy die data)
    wafers = [{k: v for k, v in w.items() if not k.startswith("_")} for w in all_raw]

    # top 10 by defect_count desc (include die/defect data for rendering)
    top10_sorted = sorted(all_raw, key=lambda w: w["defect_count"], reverse=True)[:10]
    top_wafers = [
        {**{k: v for k, v in w.items() if not k.startswith("_")},
         "dies":    w["_dies"],
         "defects": w["_defects"]}
        for w in top10_sorted
    ]

    counts = [w["defect_count"] for w in wafers]
    yields = [w["yield_pct"]    for w in wafers]
    n      = len(wafers)
    avg_c  = sum(counts) / n
    avg_y  = sum(yields)  / n
    cov    = sum((c - avg_c) * (y - avg_y) for c, y in zip(counts, yields)) / n
    std_c  = math.sqrt(sum((c - avg_c) ** 2 for c in counts) / n) or 1e-9
    std_y  = math.sqrt(sum((y - avg_y) ** 2 for y in yields)  / n) or 1e-9
    corr   = round(cov / (std_c * std_y), 3)

    avg_kill  = round(sum(w["kill_rate_pct"] for w in wafers) / n, 1)
    high_risk = [w for w in wafers if w["defect_count"] > 0 and w["kill_rate_pct"] >= 30]

    return {
        "lot_id":            lot_id,
        "defect_type":       defect_type,
        "wafers":            wafers,
        "top_wafers":        top_wafers,
        "correlation":       corr,
        "avg_yield_pct":     round(avg_y, 1),
        "avg_kill_rate_pct": avg_kill,
        "high_risk_wafers":  len(high_risk),
        "kill_prob_base":    KILL_PROB_ADD.get(defect_type, 0.1),
    }


def _mock_defect_summary(lot_id: str) -> dict:
    total_by_type: dict = {}
    best_wafer, best_count = 1, 0
    for w in range(1, 6):
        dm = _mock_defect_map(lot_id, w)
        if len(dm["defects"]) > best_count:
            best_wafer, best_count = w, len(dm["defects"])
        for t, c in dm["type_counts"].items():
            total_by_type[t] = total_by_type.get(t, 0) + c
    type_list = ", ".join(f"{k}: {v}건" for k, v in sorted(total_by_type.items(), key=lambda x: -x[1]))
    return {
        "lot_id":              lot_id,
        "sampled_wafers":      5,
        "highest_defect_wafer": best_wafer,
        "highest_defect_count": best_count,
        "total_by_type":       total_by_type,
        "dominant_type":       max(total_by_type, key=total_by_type.get) if total_by_type else "PARTICLE",
        "chart_tag":           f"[DEFECT_MAP:{lot_id}:{best_wafer}]",
        "follow_up":           f"Defect Map 태그를 포함하고, 요약 후 '어떤 Defect 유형의 Trend를 확인하시겠어요? ({type_list})' 라고 물어보세요.",
    }


def _mock_defect_trend_summary(lot_id: str, defect_type: str) -> dict:
    full = _mock_defect_trend_full(lot_id, defect_type)
    return {
        "lot_id":        lot_id,
        "defect_type":   defect_type,
        "avg_per_slot":  full["avg"],
        "ucl":           full["ucl"],
        "ooc_count":     len(full["ooc"]),
        "chart_tag":     f"[DEFECT_TREND:{lot_id}:{defect_type}]",
        "follow_up":     "Defect Trend 태그를 포함하고, '해당 Defect가 발생한 Wafer의 수율 데이터도 분석하시겠어요?' 라고 물어보세요.",
    }


def _mock_yield_defect_summary(lot_id: str, wafer_no: int) -> dict:
    full = _mock_yield_defect(lot_id, wafer_no)
    return {
        "lot_id":          lot_id,
        "wafer_no":        wafer_no,
        "wafer_yield_pct": full["wafer_yield_pct"],
        "kill_analysis":   full["kill_analysis"],
        "chart_tag":       f"[YIELD_DEFECT:{lot_id}:{wafer_no}]",
    }

