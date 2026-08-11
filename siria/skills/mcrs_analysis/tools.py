"""MCRS 분석 skill 의 tool — 같은 skill 의 services/ 를 호출하는 얇은 wrapper.

tool 은 두 계층으로 나뉜다:

  조회 계층 (범용)  get_process_context, get_insp_map, get_review_images,
                    get_pm_history, get_step_trend, get_insp_map_history,
                    get_eq_insp_coverage
                    → MCRS 발생 여부와 무관하게 동작한다. 단발 질문에 그대로 쓴다.

  MCRS 계층 (특화)  get_mcrs_issues, compare_pm_effect
                    → MCRS 이슈를 다루거나 그것을 기준으로 판단한다.

모든 tool 은 (lot_id, step_id) 만 앵커로 받고 장비·device·슬롯은 공정 이력에서
되찾는다. LLM 이 아직 조회하지 않은 eq_id 를 지어내서 넘기는 사고를 막기 위한 것이다.
"""
from langchain_core.tools import tool

from tools.common import safe_tool
from tools.registry import register

from .services import context, insp, mcrs, pm, review


def _ctx_line(ctx: dict) -> str:
    """모든 응답 첫 줄에 붙는 컨텍스트 요약."""
    if ctx["mcrs"]:
        issue = ctx["mcrs"]
        tail = f" | {issue['mcrs_code']} 슬롯 {issue['slot_no']} {issue['defect_count']}ea"
    else:
        tail = " | MCRS 이슈 없음"
    return (
        f"Lot {ctx['lot_id']} / {ctx['step_id']} ({ctx['step_desc']})"
        f" | 장비 {ctx['eq_id']} | device {ctx['device_id']}{tail}"
    )


# ============================================================ 조회 계층 (범용)

@tool
@safe_tool
def get_process_context(lot_id: str, step_id: str) -> str:
    """Lot 이 특정 공정을 지나갈 때의 장비·device·처리 시각과 MCRS 발생 여부를 조회한다.

    언제 사용: "이 Lot 이 어느 장비에서 돌았어?" 처럼 공정 컨텍스트만 필요할 때,
    또는 다른 조회 전에 공정 ID 가 유효한지 확인하고 싶을 때.

    다른 tool 과의 구분:
    - MCRS 이슈 목록 전체가 필요하면 get_mcrs_issues 를 사용한다.
    - Lot 의 현재 위치/상태는 get_lot_info 를 사용한다 (이건 과거 특정 공정 시점이다).

    Args:
        lot_id: Lot 번호 (예: TE2FE35). 대소문자 무관.
        step_id: 공정 ID (예: INSP-CMP-01). 이 Lot 이 지나가지 않은 공정이면
            지나간 공정 목록을 알려주며 실패한다.
    """
    ctx = mcrs.resolve(lot_id, step_id)
    lines = [_ctx_line(ctx), f"처리 시각: {ctx['processed_at']} | 슬롯 수: {ctx['slot_count']}"]
    route = context.get_route(ctx["lot_id"])
    lines.append("이 Lot 이 지나간 공정: " + ", ".join(s["step_id"] for s in route))
    return "\n".join(lines)


@tool
@safe_tool
def get_insp_map(lot_id: str, step_id: str) -> str:
    """지정한 공정의 INSP MAP 이미지를 해당 Lot 의 전체 슬롯에 대해 조회한다.

    언제 사용: "이 Lot 의 이 공정 INSP 결과 보여줘" 같은 단발 요청에 바로 사용한다.
    MCRS 가 없어도 동작하며, 있으면 해당 슬롯에 ★ 표시가 붙는다.

    다른 tool 과의 구분:
    - 같은 슬롯의 **과거 공정** MAP 을 이어서 보려면 get_insp_map_history 를 사용한다.
    - 결함 하나하나의 SEM 확대 이미지는 get_review_images 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
    """
    data = insp.get_insp_map(lot_id, step_id)
    ctx = data["ctx"]
    lines = [_ctx_line(ctx), ""]
    if ctx["mcrs"]:
        lines.append(
            f"MCRS 슬롯 {ctx['mcrs']['slot_no']}: {ctx['mcrs']['defect_count']}ea"
            f" | 나머지 슬롯 평균 {data['others_mean']}ea (최대 {data['others_max']}ea)"
        )
    else:
        lines.append(
            f"전 슬롯 평균 {data['others_mean']}ea (최대 {data['others_max']}ea)"
            f" | 이 공정 기준선 {data['baseline']}ea"
        )
    lines += ["", "slot | defect | image"]
    for slot in data["slots"]:
        mark = " ★MCRS" if slot["is_mcrs_slot"] else ""
        lines.append(
            f"{slot['slot_no']:>2} | {slot['defect_count']:>4}ea{mark} | {slot['image_url']}"
        )
    lines += ["", "위 image URL 을 모두 사용자에게 이미지로 표시하세요."]
    return "\n".join(lines)


@tool
@safe_tool
def get_review_images(lot_id: str, step_id: str, slot_no: int | None = None) -> str:
    """지정한 슬롯의 결함 좌표별 REV(리뷰) 이미지를 조회한다.

    같은 좌표에서 찍힌 이미지는 rev_1, rev_2, rev_3, rev_4 로 묶여서 나온다.
    같은 결함을 배율·시점 달리해 찍은 것이므로 좌표 단위로 묶어서 표시한다.

    언제 사용: INSP MAP 으로 이상 슬롯을 확인한 뒤 결함의 실제 형상을 봐야 할 때.

    다른 tool 과의 구분:
    - 슬롯 전체의 결함 분포(MAP)는 get_insp_map 을 사용한다. 이 tool 은 개별 결함의
      확대 이미지다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
        slot_no: 볼 슬롯 번호. 생략하면 MCRS 발생 슬롯을 사용한다. MCRS 가 없는
            공정이면 생략할 수 없으므로 사용자에게 슬롯 번호를 물어본다.
    """
    data = review.get_review_images(lot_id, step_id, slot_no)
    lines = [
        _ctx_line(data["ctx"]),
        f"슬롯 {data['slot_no']} | 결함 좌표 {data['coord_total']}개 중 "
        f"{data['coord_shown']}개 표시",
        "",
    ]
    for coord in data["coords"]:
        lines.append(
            f"{coord['coord_id']} (x={coord['x']}, y={coord['y']})"
            f" | {coord['defect_type']} {coord['size_um']}um"
            f" | rev {len(coord['revs'])}장"
        )
        for rev in coord["revs"]:
            lines.append(f"    rev_{rev['rev']}: {rev['image_url']}")
    lines += [
        "",
        "표시 규칙: 좌표별로 rev_1~rev_N 을 한 줄에 나란히 놓아 같은 결함의 "
        "여러 이미지를 비교할 수 있게 하세요.",
    ]
    return "\n".join(lines)


@tool
@safe_tool
def get_pm_history(lot_id: str, step_id: str, days: int = 90) -> str:
    """해당 공정을 처리한 장비의 PM 이력과 '기준 시각까지 며칠 지났는지'를 조회한다.

    언제 사용: "이 장비 PM 언제 했어?" 같은 단발 요청, 또는 원인이 장비 상태인지
    확인할 때. PM 직후 문제면 PM 작업 자체를, 주기를 넘겼으면 PM 지연을 의심한다.

    다른 tool 과의 구분:
    - PM 을 기준으로 한 전후 데이터 비교까지 필요하면 compare_pm_effect 를 사용한다.
      이 tool 은 PM 이 '언제 됐는지'만 알려준다.
    - 장비의 현재 상태(RUN/IDLE/DOWN)는 get_eq_status 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 90일.
    """
    data = pm.get_pm_history(lot_id, step_id, days)
    last = data["last_pm"]
    ctx = data["ctx"]
    label = "MCRS 발생" if ctx["mcrs"] else "공정 처리"
    lines = [
        _ctx_line(ctx),
        f"PM 이력 — 장비 {data['eq_id']} (최근 {data['days']}일, "
        f"정기 주기 약 {data['pm_cycle_days']}일)",
        f"{label} 시각: {ctx['processed_at']}",
        f"직전 PM: {last['started_at']} ({last['pm_type']}, {last['main_work']})"
        f" → {data['days_since_last_pm']}일 경과",
        "",
        "전체 이력:",
    ]
    for rec in data["records"]:
        lines.append(
            f"  {rec['started_at']} | {rec['pm_type']} | {rec['main_work']}"
            f" | {rec['duration_h']}h | {rec['pm_id']}"
        )
    return "\n".join(lines)


@tool
@safe_tool
def get_step_trend(lot_id: str, step_id: str, days: int = 30) -> str:
    """해당 공정의 최근 N일 검사 데이터를 일 단위로 조회한다 (trend 작성용).

    언제 사용: "이 공정 최근 추이 보여줘" 같은 단발 요청, 또는 문제가 갑자기 튄
    것인지 서서히 나빠지고 있었는지 확인할 때. 기본 30일.

    다른 tool 과의 구분:
    - PM 시점을 기준으로 구간을 나눈 비교가 필요하면 compare_pm_effect 를 사용한다.
      이 tool 은 구간 구분 없이 날짜별 원본 추이만 준다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 30일.
    """
    data = pm.get_step_trend(lot_id, step_id, days)
    s = data["summary"]
    lines = [
        _ctx_line(data["ctx"]),
        f"최근 {data['days']}일 검사 추이 | 공정 기준선 {data['baseline']}ea",
        f"전체: n={s['count']}, 평균 {s['mean']}ea, 표준편차 {s['std']}, "
        f"범위 {s['min']}~{s['max']}ea",
        "",
        "date | mean_defect | n",
    ]
    for point in data["points"]:
        lines.append(f"{point['date']} | {point['mean_defect']:>6} | {point['sample_count']}")
    lines += ["", "위 데이터로 trend 차트를 그려 사용자에게 표시하세요."]
    return "\n".join(lines)


@tool
@safe_tool
def get_insp_map_history(lot_id: str, step_id: str, slot_no: int | None = None) -> str:
    """같은 Lot/슬롯이 지나온 과거 검사 공정의 INSP MAP 을 오래된 순으로 조회한다.

    대상 공정은 공정 이력에서 뽑으므로 MCRS 가 나지 않은 공정도 포함된다.

    언제 사용: 해당 슬롯이 원래부터 나빴는지, 이번 공정에서 갑자기 나빠졌는지
    확인할 때. 결함 발생 공정을 좁히는 데 쓴다.

    다른 tool 과의 구분:
    - 현재 공정의 슬롯별 MAP 은 get_insp_map 을 사용한다 (같은 시점, 여러 슬롯).
      이 tool 은 같은 슬롯의 여러 시점이다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01). 이 공정 '이전' 이력을 찾는다.
        slot_no: 추적할 슬롯 번호. 생략하면 MCRS 발생 슬롯을 사용한다.
    """
    data = insp.get_insp_map_history(lot_id, step_id, slot_no)
    lines = [
        _ctx_line(data["ctx"]),
        f"슬롯 {data['slot_no']} INSP MAP 이력 (오래된 순)",
        "",
        "step | 검사시각 | 장비 | defect | image",
    ]
    for item in data["timeline"]:
        if item["slot_has_mcrs"]:
            mark = " ★MCRS"
        elif item["step_mcrs_slot"] is not None:
            # 그 공정에 MCRS 는 있었지만 다른 슬롯이다 — 혼동하지 않게 명시한다.
            mark = f" (이 공정 MCRS 는 슬롯 {item['step_mcrs_slot']})"
        else:
            mark = ""
        cur = " ←현재" if item.get("is_current") else ""
        lines.append(
            f"{item['step_id']} ({item['step_desc']}) | {item['inspected_at']}"
            f" | {item['eq_id']} | {item['defect_count']}ea{mark}{cur}"
            f" | {item['image_url']}"
        )
    if len(data["timeline"]) == 1:
        lines += ["", "주의: 이 공정 이전의 검사 이력이 없어 비교 대상이 없습니다."]
    else:
        lines += ["", "위 MAP 들을 시간 순으로 나란히 표시해 결함 증가 시점을 보여주세요."]
    return "\n".join(lines)


@tool
@safe_tool
def get_eq_insp_coverage(lot_id: str, step_id: str, days: int = 30) -> str:
    """해당 공정을 처리한 장비를 지나간 '다른 device / 다른 공정' 의 검사 실적을 조회한다.

    언제 사용: 장비 자체의 문제인지, 이 device/공정 조합에만 나타나는 문제인지
    가를 때. 다른 device 도 같이 나쁘면 장비 이슈, 이 조합만 나쁘면 공정/제품 이슈다.

    다른 tool 과의 구분:
    - 같은 Lot 안의 다른 슬롯 비교는 get_insp_map 이다. 이 tool 은 같은 장비를
      지나간 **다른 Lot/device** 를 본다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 30일.
    """
    data = insp.get_eq_insp_coverage(lot_id, step_id, days)
    ctx = data["ctx"]
    lines = [
        _ctx_line(ctx),
        f"장비 {ctx['eq_id']} 교차 확인 — 최근 {data['days']}일, "
        f"기준선 {data['baseline']}ea, 조회 조합({ctx['device_id']}/{ctx['step_id']}) 제외",
        "",
    ]
    if not data["rows"]:
        lines.append("해당 기간에 이 장비를 지나간 다른 device/공정 검사 실적이 없습니다.")
        return "\n".join(lines)

    lines.append("device | step | lot수 | 평균 defect | 최종 검사 | 이상")
    for row in data["rows"]:
        flag = "★" if row["abnormal"] else "-"
        lines.append(
            f"{row['device_id']} | {row['step_id']} | {row['lot_count']} | "
            f"{row['mean_defect']}ea | {row['last_inspected_at']} | {flag}"
        )
    lines += [
        "",
        f"이상 표시된 조합 {data['abnormal_count']}건. "
        "1건 이상이면 장비 공통 이슈 가능성이, 0건이면 해당 device/공정 특유의 "
        "이슈 가능성이 큽니다.",
    ]
    return "\n".join(lines)


# ========================================================== MCRS 계층 (특화)

@tool
@safe_tool
def get_mcrs_issues(lot_id: str) -> str:
    """Lot 1개에서 발생한 MCRS 이슈 목록(공정, 장비, 발생 슬롯, 발생 시각)을 조회한다.

    언제 사용: 사용자가 Lot 번호만 주고 MCRS 를 언급했을 때, 어느 공정을 볼지
    정하기 위해 먼저 호출한다. 이슈가 없으면 "없음" 을 알려준다 (실패가 아니다).

    다른 tool 과의 구분:
    - 사용자가 **공정까지 이미 지정했다면** 이 tool 없이 해당 조회 tool 을 바로
      호출해도 된다.
    - 특정 공정의 장비/device 만 필요하면 get_process_context 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35). 대소문자 무관.
    """
    issues = mcrs.get_mcrs_issues(lot_id)
    if not issues:
        route = context.get_route(lot_id)
        return (
            f"Lot {context.normalize_lot_id(lot_id)}: MCRS 이슈 없음.\n"
            "지나간 공정: " + ", ".join(s["step_id"] for s in route) + "\n\n"
            "MCRS 는 없지만 일반 검사 데이터 조회는 가능합니다 "
            "(get_insp_map, get_step_trend 등)."
        )

    lines = [f"MCRS 이슈 {len(issues)}건 (Lot: {context.normalize_lot_id(lot_id)})", ""]
    for idx, issue in enumerate(issues, start=1):
        lines.append(
            f"[{idx}] {issue['step_id']} ({issue['step_desc']})"
            f" | 장비 {issue['eq_id']}"
            f" | device {issue['device_id']}"
            f" | 발생 슬롯 {issue['slot_no']}"
            f" | {issue['mcrs_code']} {issue['defect_count']}ea"
            f" | {issue['detected_at']}"
        )
    if len(issues) > 1:
        lines += [
            "",
            "다음 행동: 위 목록을 사용자에게 그대로 보여주고 어느 공정을 볼지 "
            "물어본 뒤, 답을 받기 전에는 다른 tool 을 호출하지 마세요.",
        ]
    else:
        lines += ["", f"이슈가 1건뿐이므로 {issues[0]['step_id']} 로 바로 분석을 진행하세요."]
    return "\n".join(lines)


@tool
@safe_tool
def compare_pm_effect(lot_id: str, step_id: str, days: int = 30) -> str:
    """직전 PM 시점을 기준으로 검사 데이터를 구간별로 나눠 통계 비교한다.

    MCRS 가 있으면 3구간(PM 이전 / PM 이후~MCRS 전 / MCRS 이후), 없으면 2구간
    (PM 이전 / PM 이후)으로 나눈다.

    언제 사용: PM 이 원인인지 판단할 때. get_pm_history 와 get_step_trend 를 각각
    부른 뒤 직접 평균을 계산하지 말고 이 tool 을 사용한다 — 계산은 이 tool 이 한다.

    다른 tool 과의 구분:
    - PM 날짜만 필요하면 get_pm_history, 날짜별 원본 추이만 필요하면
      get_step_trend 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 공정 ID (예: INSP-CMP-01).
        days: 비교에 사용할 데이터 기간(일). 기본 30일.
    """
    data = pm.compare_pm_effect(lot_id, step_id, days)
    ctx = data["ctx"]
    last = data["last_pm"]
    labels = {
        "before_pm": "PM 이전 (기준선)",
        "after_pm": "PM 이후~기준시각 전" if data["has_mcrs"] else "PM 이후",
        "after_mcrs": "MCRS 발생 이후",
    }
    ref_label = "MCRS 발생" if data["has_mcrs"] else "공정 처리"
    lines = [
        _ctx_line(ctx),
        f"직전 PM: {last['started_at']} ({last['pm_type']}, {last['main_work']})",
        f"{ref_label}: {data['reference_at']} (PM 후 {data['days_since_last_pm']}일, "
        f"정기 주기 {data['pm_cycle_days']}일)",
        "",
    ]
    for key, window in data["windows"].items():
        label = labels[key]
        if window["count"] == 0:
            lines.append(f"{label}: 해당 구간 데이터 없음")
        else:
            lines.append(
                f"{label}: n={window['count']}, 평균 {window['mean']}ea, "
                f"표준편차 {window['std']}, 범위 {window['min']}~{window['max']}ea"
            )
    lines += [
        "",
        "판정 가이드: PM 이후 구간이 PM 이전과 비슷하면 PM 자체는 정상 수행된 것이고, "
        "PM 이후 구간부터 나빠졌으면 PM 작업을 의심합니다.",
    ]
    if data["has_mcrs"]:
        lines.append("MCRS 이후 구간이 여전히 높으면 원인이 해소되지 않은 것입니다.")
    return "\n".join(lines)


register(get_process_context)
register(get_insp_map)
register(get_review_images)
register(get_pm_history)
register(get_step_trend)
register(get_insp_map_history)
register(get_eq_insp_coverage)
register(get_mcrs_issues)
register(compare_pm_effect)
