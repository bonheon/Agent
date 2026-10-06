"""
전일 이슈 리포트 Mock 데이터.
WIP 변동 / Hold 현황 / Defect 이슈 / 장비 문제를 종합하고
우선 대응 액션을 자동 생성합니다.
"""
import math
import random
from datetime import datetime, timedelta

# ── 지원 Area 공정 그룹 ──────────────────────────────────────────
_AREA_GROUPS = {
    "M14 CMP": [
        {"group_id": "STI-CMP",  "group_name": "STI CMP",     "eq_ids": ["CMP01A","CMP01B","CMP01C","CMP01D"], "move_target": 48},
        {"group_id": "POLY-CMP", "group_name": "Poly CMP",    "eq_ids": ["CMP02A","CMP02B","CMP02C"],          "move_target": 36},
        {"group_id": "W-CMP",    "group_name": "W Plug CMP",  "eq_ids": ["CMP03A","CMP03B","CMP03C","CMP03D"], "move_target": 52},
        {"group_id": "Cu-CMP1",  "group_name": "Cu CMP 1st",  "eq_ids": ["CMP04A","CMP04B","CMP04C"],          "move_target": 40},
        {"group_id": "Cu-CMP2",  "group_name": "Cu CMP 2nd",  "eq_ids": ["CMP05A","CMP05B"],                   "move_target": 24},
    ],
}

_HOLD_REASONS = [
    {"code": "PARTICLE_DEFECT",  "desc": "파티클 결함 기준 초과"},
    {"code": "CD_OOC",           "desc": "CD 규격 이탈"},
    {"code": "THICKNESS_OOC",    "desc": "박막 두께 규격 이탈"},
    {"code": "SCRATCH_DEFECT",   "desc": "스크래치 결함 기준 초과"},
    {"code": "BRIDGE_DEFECT",    "desc": "Bridge 결함 기준 초과"},
]

_DOWN_CAUSES = [
    "슬러리 공급 밸브 오작동",
    "압력 센서 이상",
    "폴리싱 헤드 진동 이상",
    "드레서 암 오작동",
    "웨이퍼 로딩 에러",
    "냉각수 유량 이상",
]

_LOT_POOL = [
    "TE2FE35","TE2FE36","TE2FE37","TE2FE38","TE2FE39","TE2FE40",
    "TE2FE41","TE2FE42","TE2FE43","TE2FE44","TE2FE45","TE2FE46",
    "TE2FC10","TE2FC11","TE2FC12","TE2FC13","TE2FC14","TE2FC15",
]


def _area_key(area_input: str) -> str:
    norm = area_input.strip().upper()
    for k in _AREA_GROUPS:
        if k.upper() in norm or norm in k.upper():
            return k
    return "M14 CMP"


def _rng(seed_str: str) -> random.Random:
    return random.Random(hash(seed_str) % 2**31)


def get_daily_report(area_input: str, report_date: str | None = None) -> dict:
    """
    area_input: "M14 CMP" 등
    report_date: "YYYY-MM-DD" (None이면 전일)
    """
    key = _area_key(area_input)
    groups = _AREA_GROUPS.get(key, _AREA_GROUPS["M14 CMP"])

    if report_date is None:
        yesterday = (datetime.now() - timedelta(days=1)).date()
    else:
        yesterday = datetime.strptime(report_date, "%Y-%m-%d").date()

    date_str  = yesterday.strftime("%Y-%m-%d")
    date_seed = int(yesterday.strftime("%Y%m%d"))

    # ── 1. WIP 그룹별 변동 ──────────────────────────────────────
    wip_groups = []
    total_wip_start = total_wip_end = 0
    total_move = total_move_target = 0

    for g in groups:
        rng = _rng(f"{key}-wip-{g['group_id']}-{date_seed}")
        wip_start  = rng.randint(10, 22)
        move_out   = int(g["move_target"] * rng.uniform(0.75, 1.05))
        move_in    = move_out + rng.randint(-5, 5)
        wip_end    = max(0, wip_start + move_in - move_out)
        achieve_pct = round(move_out / g["move_target"] * 100, 1)

        total_wip_start += wip_start
        total_wip_end   += wip_end
        total_move      += move_out
        total_move_target += g["move_target"]

        wip_groups.append({
            "group_id":    g["group_id"],
            "group_name":  g["group_name"],
            "wip_start":   wip_start,
            "wip_end":     wip_end,
            "move_in":     move_in,
            "move_out":    move_out,
            "move_target": g["move_target"],
            "achieve_pct": achieve_pct,
            "delta":       wip_end - wip_start,
        })

    move_achieve_pct = round(total_move / total_move_target * 100, 1)

    # ── 2. 장비 이슈 (DOWN / PM) ────────────────────────────────
    equipment_issues = []
    down_eq_set: set[str] = set()

    for g in groups:
        for eq_id in g["eq_ids"]:
            rng = _rng(f"{key}-eq-{eq_id}-{date_seed}")
            roll = rng.random()
            if roll < 0.12:   # DOWN 발생
                down_h = round(rng.uniform(1.5, 10.0), 1)
                still_down = rng.random() < 0.45  # 45% 는 아직 복구 안됨
                cause = rng.choice(_DOWN_CAUSES)
                wip_waiting = rng.randint(4, 16) if still_down else 0
                # Defect 스파이크와 연관 여부 (DOWN 전 장비 이상 징후)
                defect_corr = rng.random() < 0.55

                equipment_issues.append({
                    "eq_id":           eq_id,
                    "process":         g["group_name"],
                    "group_id":        g["group_id"],
                    "issue_type":      "DOWN",
                    "down_start":      f"{date_str} {rng.randint(8,18):02d}:{rng.randint(0,59):02d}",
                    "down_end":        None if still_down else f"{date_str} {rng.randint(18,23):02d}:{rng.randint(0,59):02d}",
                    "down_time_h":     down_h + (rng.uniform(12, 20) if still_down else 0),
                    "cause":           cause,
                    "status_now":      "DOWN" if still_down else "RUNNING",
                    "wip_waiting":     wip_waiting,
                    "defect_correlated": defect_corr,
                })
                if still_down:
                    down_eq_set.add(eq_id)

            elif roll < 0.18:  # PM
                equipment_issues.append({
                    "eq_id":      eq_id,
                    "process":    g["group_name"],
                    "group_id":   g["group_id"],
                    "issue_type": "PM",
                    "down_start": f"{date_str} {rng.randint(8,14):02d}:00",
                    "down_end":   f"{date_str} {rng.randint(15,19):02d}:00",
                    "down_time_h": round(rng.uniform(2.0, 6.0), 1),
                    "cause":      "정기 예방정비 (PM)",
                    "status_now": "RUNNING",
                    "wip_waiting": 0,
                    "defect_correlated": False,
                })

    # ── 3. Hold 이력 ────────────────────────────────────────────
    hold_lots: list[dict] = []
    rng_hold = _rng(f"{key}-hold-{date_seed}")
    n_holds = rng_hold.randint(4, 9)

    used_lots: set[str] = set()
    for _ in range(n_holds):
        lot = rng_hold.choice([l for l in _LOT_POOL if l not in used_lots] or _LOT_POOL)
        used_lots.add(lot)
        reason = rng_hold.choice(_HOLD_REASONS)
        grp    = rng_hold.choice(groups)
        eq_id  = rng_hold.choice(grp["eq_ids"])
        status = "OPEN" if rng_hold.random() < 0.55 else "RELEASED"
        hold_lots.append({
            "lot_id":      lot,
            "process":     grp["group_name"],
            "group_id":    grp["group_id"],
            "equipment":   eq_id,
            "reason_code": reason["code"],
            "reason_desc": reason["desc"],
            "hold_time":   f"{date_str} {rng_hold.randint(8,20):02d}:{rng_hold.randint(0,59):02d}",
            "status":      status,
        })

    # by_reason 집계
    by_reason: dict[str, int] = {}
    by_process: dict[str, int] = {}
    for h in hold_lots:
        by_reason[h["reason_code"]] = by_reason.get(h["reason_code"], 0) + 1
        by_process[h["process"]] = by_process.get(h["process"], 0) + 1

    hold_summary = {
        "new_holds":     len(hold_lots),
        "open_holds":    sum(1 for h in hold_lots if h["status"] == "OPEN"),
        "released_holds": sum(1 for h in hold_lots if h["status"] == "RELEASED"),
        "lots":          hold_lots,
        "by_reason":     [
            {"reason_code": k, "count": v,
             "pct": round(v / len(hold_lots) * 100, 1)}
            for k, v in sorted(by_reason.items(), key=lambda x: -x[1])
        ],
        "by_process":    [
            {"process": k, "count": v,
             "alert": v >= 2}
            for k, v in sorted(by_process.items(), key=lambda x: -x[1])
        ],
    }

    # ── 4. Defect 스파이크 분석 ─────────────────────────────────
    defect_issues: list[dict] = []
    defect_types = ["PARTICLE", "SCRATCH", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"]

    for g in groups:
        for eq_id in g["eq_ids"]:
            rng_d = _rng(f"{key}-defect-{eq_id}-{date_seed}")
            baseline = rng_d.randint(30, 80)
            # DOWN 직전 장비 또는 Hold 연관 장비는 스파이크 확률 높음
            spike_prob = 0.25
            if eq_id in down_eq_set:
                spike_prob = 0.70
            if any(h["equipment"] == eq_id for h in hold_lots):
                spike_prob = max(spike_prob, 0.55)

            if rng_d.random() < spike_prob:
                spike_ratio = round(rng_d.uniform(1.6, 3.5), 2)
                count = int(baseline * spike_ratio)
                dom_type = rng_d.choice(defect_types[:3])  # 주로 앞 3개
                affected_lots_raw = [h["lot_id"] for h in hold_lots if h["equipment"] == eq_id]
                if not affected_lots_raw:
                    affected_lots_raw = rng_d.sample(_LOT_POOL, rng_d.randint(1, 3))

                defect_issues.append({
                    "process":       g["group_name"],
                    "group_id":      g["group_id"],
                    "equipment":     eq_id,
                    "defect_count":  count,
                    "baseline":      baseline,
                    "spike_ratio":   spike_ratio,
                    "spike_pct":     round((spike_ratio - 1) * 100, 0),
                    "dominant_type": dom_type,
                    "affected_lots": affected_lots_raw[:4],
                    "still_down":    eq_id in down_eq_set,
                })

    defect_issues.sort(key=lambda x: -x["defect_count"])

    # ── 5. 우선 대응 액션 생성 (교차 분석) ─────────────────────
    priority_actions: list[dict] = []

    # P1: 현재 DOWN 중 + WIP 대기 + Defect 연관
    for eq in sorted(equipment_issues, key=lambda e: -(e.get("wip_waiting", 0))):
        if eq["status_now"] != "DOWN":
            continue
        defs = [d for d in defect_issues if d["equipment"] == eq["eq_id"]]
        holds = [h for h in hold_lots if h["equipment"] == eq["eq_id"]]
        wip_w = eq["wip_waiting"]

        details = [
            f"전일 {eq['down_start'][11:]} 부터 현재까지 DOWN ({round(eq['down_time_h'], 1)}h 경과)",
            f"{eq['process']}에 {wip_w}개 lot 대기 (WIP 병목)",
        ]
        if defs:
            details.append(f"DOWN 전 Defect 스파이크: {defs[0]['dominant_type']} {defs[0]['spike_pct']:.0f}% 초과")
        if holds:
            lot_str = ", ".join(h["lot_id"] for h in holds[:3])
            details.append(f"Hold 연관 lot: {lot_str}")

        urgency = "HIGH" if (wip_w >= 8 or eq["down_time_h"] >= 8 or defs) else "MEDIUM"
        action_str = f"{eq['cause']} 점검 및 복구. 대기 lot은 동일 공정 대체 장비로 분산 투입 검토."
        if defs:
            action_str += f" 복구 후 초도 lot Defect 면밀 확인 필수."

        priority_actions.append({
            "priority":       len(priority_actions) + 1,
            "urgency":        urgency,
            "category":       "장비 복구",
            "target":         eq["eq_id"],
            "target_process": eq["process"],
            "summary":        f"{eq['eq_id']} {round(eq['down_time_h'], 1)}h DOWN · {wip_w}lot 대기" + (" · Defect 연관" if defs else ""),
            "details":        details,
            "suggested_action": action_str,
        })

    # P2: Defect 스파이크 (장비 복구 아직 안된 건 외)
    for d in defect_issues:
        if d["equipment"] in down_eq_set:
            continue  # 이미 P1에서 다룸
        holds = [h for h in hold_lots if h["equipment"] == d["equipment"]]
        details = [
            f"전일 Defect {d['defect_count']}건 (기준 대비 +{d['spike_pct']:.0f}%, 스파이크 비율 {d['spike_ratio']}×)",
            f"주요 Defect 유형: {d['dominant_type']}",
        ]
        if holds:
            details.append(f"관련 Hold lot: {', '.join(h['lot_id'] for h in holds[:3])}")
        details.append("최근 레시피 변경 이력 및 슬러리/드레서 상태 확인 필요")

        priority_actions.append({
            "priority":       len(priority_actions) + 1,
            "urgency":        "MEDIUM",
            "category":       "Defect 원인 조사",
            "target":         d["equipment"],
            "target_process": d["process"],
            "summary":        f"{d['equipment']} {d['dominant_type']} 스파이크 +{d['spike_pct']:.0f}% ({d['defect_count']}건)",
            "details":        details,
            "suggested_action": f"{d['equipment']} 점검. 슬러리 농도·패드 상태·드레서 조건 확인. 다음 2 lot 집중 모니터링.",
        })

    # P3: Open Hold lot 처리 (장비 이슈 외)
    open_holds = [h for h in hold_lots if h["status"] == "OPEN"]
    if open_holds:
        top_reason_code = hold_summary["by_reason"][0]["reason_code"] if hold_summary["by_reason"] else "UNKNOWN"
        lot_str = ", ".join(h["lot_id"] for h in open_holds[:4])
        priority_actions.append({
            "priority":       len(priority_actions) + 1,
            "urgency":        "MEDIUM" if len(open_holds) >= 3 else "LOW",
            "category":       "Hold Lot 처리",
            "target":         f"{len(open_holds)}건",
            "target_process": "전 공정",
            "summary":        f"Open Hold {len(open_holds)}건 — 주요 원인: {top_reason_code}",
            "details":        [
                f"Open 상태 lot: {lot_str}" + ("..." if len(open_holds) > 4 else ""),
                f"주요 원인: {top_reason_code} ({hold_summary['by_reason'][0]['count']}건)",
                "수율 예측 분석 후 Disposition 결정 필요",
            ],
            "suggested_action": "Chip Kill 분석 완료 후 Rework / Scrap / 조건부 진행 결정. 오늘 중 Disposition 마감 권고.",
        })

    # P4: PM 장비 당일 재투입 모니터링
    pm_done = [e for e in equipment_issues if e["issue_type"] == "PM" and e["status_now"] == "RUNNING"]
    for e in pm_done[:2]:
        priority_actions.append({
            "priority":       len(priority_actions) + 1,
            "urgency":        "LOW",
            "category":       "PM 복구 확인",
            "target":         e["eq_id"],
            "target_process": e["process"],
            "summary":        f"{e['eq_id']} PM 완료 — 초도 lot 품질 모니터링 필요",
            "details":        [
                f"PM 진행: {e['down_start'][11:]} ~ {(e['down_end'] or '진행중')[11:]} ({e['down_time_h']}h)",
                "PM 후 첫 2 lot는 Defect 및 두께 결과 면밀 확인",
                "이상 발생 시 즉시 Hold 처리",
            ],
            "suggested_action": f"{e['eq_id']} 초도 처리 lot 결과 확인. SPC 자동 판정 외 수동 리뷰 병행.",
        })

    # priority 번호 재정렬
    for i, a in enumerate(priority_actions):
        a["priority"] = i + 1

    # ── KPI 집계 ────────────────────────────────────────────────
    kpi = {
        "total_wip_start":    total_wip_start,
        "total_wip_end":      total_wip_end,
        "wip_delta":          total_wip_end - total_wip_start,
        "total_move":         total_move,
        "total_move_target":  total_move_target,
        "move_achieve_pct":   move_achieve_pct,
        "new_holds":          hold_summary["new_holds"],
        "open_holds":         hold_summary["open_holds"],
        "defect_spike_count": len(defect_issues),
        "down_count":         sum(1 for e in equipment_issues if e["issue_type"] == "DOWN"),
        "still_down_count":   sum(1 for e in equipment_issues if e["status_now"] == "DOWN"),
        "pm_count":           sum(1 for e in equipment_issues if e["issue_type"] == "PM"),
    }

    return {
        "area_key":           key,
        "area_name":          f"{key} Area",
        "report_date":        date_str,
        "generated_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "kpi":                kpi,
        "wip_groups":         wip_groups,
        "hold_summary":       hold_summary,
        "defect_issues":      defect_issues,
        "equipment_issues":   equipment_issues,
        "priority_actions":   priority_actions,
    }
