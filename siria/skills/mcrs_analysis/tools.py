"""MCRS 분석 tool — 같은 skill 의 services/ 를 호출하는 얇은 wrapper.

이 파일에는 비즈니스 로직이 없다. core 호출 + LLM 이 읽을 텍스트 포맷팅만 한다.

모든 후속 tool 이 (lot_id, step_id) 만 인자로 받는 것이 이 tool 세트의 설계 핵심이다.
장비 ID·슬롯 번호·device 는 core 가 이슈 레코드에서 되찾는다. LLM 이 아직 조회하지
않은 eq_id 를 지어내서 넘기는 사고를 구조적으로 막기 위한 것이다.
"""
from langchain_core.tools import tool

from .services import insp, mcrs, pm, review
from tools.common import safe_tool
from tools.registry import register


# ---------------------------------------------------------------- 2. 이슈 조회

@tool
@safe_tool
def get_mcrs_issues(lot_id: str) -> str:
    """Lot 1개에서 발생한 MCRS 이슈 목록(공정, 장비, 발생 슬롯, 발생 시각)을 조회한다.

    언제 사용: MCRS 분석의 **반드시 첫 번째** 단계. 사용자가 Lot 번호와 함께
    MCRS 를 언급하면 다른 어떤 tool 보다 먼저 이 tool 을 호출한다.

    다른 tool 과의 구분:
    - 이 tool 이 돌려주는 step_id 가 나머지 MCRS tool 전부의 입력이 된다.
      이 tool 을 건너뛰고 다른 MCRS tool 을 호출하면 안 된다.
    - Lot 의 일반 상태(현재 위치, Hold 여부)는 get_lot_info 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35). 대소문자 무관.
    """
    issues = mcrs.get_mcrs_issues(lot_id)
    lines = [f"MCRS 이슈 {len(issues)}건 (Lot: {issues[0]['lot_id']})", ""]
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


# ------------------------------------------------------------- 4. INSP MAP

@tool
@safe_tool
def get_insp_map(lot_id: str, step_id: str) -> str:
    """선택한 공정의 INSP MAP 이미지를 동일 Lot 의 전체 슬롯에 대해 조회한다.

    언제 사용: 사용자가 볼 공정을 고른 직후. MCRS 발생 슬롯만이 아니라 같은 Lot 의
    나머지 슬롯 MAP 도 함께 나오므로, 한 슬롯만 튀는지 Lot 전체가 나쁜지 판단한다.

    다른 tool 과의 구분:
    - 같은 슬롯의 **과거 공정** MAP 을 이어서 보려면 get_insp_map_history 를 사용한다.
    - 결함 하나하나의 SEM 이미지는 get_mcrs_review_images 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: get_mcrs_issues 결과에서 사용자가 고른 공정 ID (예: INSP-CMP-01).
    """
    data = insp.get_insp_map(lot_id, step_id)
    issue = data["issue"]
    lines = [
        f"INSP MAP — Lot {issue['lot_id']} / {issue['step_id']} ({issue['step_desc']})",
        f"MCRS 슬롯 {data['mcrs_slot_no']}: {issue['defect_count']}ea"
        f" | 나머지 슬롯 평균 {data['normal_mean']}ea (최대 {data['normal_max']}ea)",
        "",
        "slot | defect | image",
    ]
    for slot in data["slots"]:
        mark = " ★MCRS" if slot["is_mcrs_slot"] else ""
        lines.append(f"{slot['slot_no']:>2} | {slot['defect_count']:>4}ea{mark} | {slot['image_url']}")
    lines += ["", "위 image URL 을 모두 사용자에게 이미지로 표시하세요."]
    return "\n".join(lines)


# --------------------------------------------------------- 5. REV 이미지

@tool
@safe_tool
def get_mcrs_review_images(lot_id: str, step_id: str, slot_no: int | None = None) -> str:
    """MCRS 발생 슬롯의 결함 좌표별 REV(리뷰) 이미지를 조회한다.

    같은 좌표에서 찍힌 이미지는 rev_1, rev_2, rev_3, rev_4 로 묶여서 나온다.
    같은 결함을 배율·시점을 달리해 찍은 것이므로 반드시 좌표 단위로 묶어서 표시한다.

    언제 사용: INSP MAP 으로 이상 슬롯을 확인한 뒤, 결함의 실제 형상을 봐야 할 때.

    다른 tool 과의 구분:
    - 슬롯 전체의 결함 분포(MAP)는 get_insp_map 을 사용한다. 이 tool 은 개별 결함의
      확대 이미지다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01).
        slot_no: 볼 슬롯 번호. 생략하면 MCRS 가 발생한 슬롯을 자동으로 사용한다.
    """
    data = review.get_review_images(lot_id, step_id, slot_no)
    issue = data["issue"]
    lines = [
        f"REV 이미지 — Lot {issue['lot_id']} / {issue['step_id']} / 슬롯 {data['slot_no']}",
        f"결함 좌표 {data['coord_total']}개 중 {data['coord_shown']}개 표시",
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


# ------------------------------------------------------------- 6. PM 이력

@tool
@safe_tool
def get_mcrs_pm_history(lot_id: str, step_id: str, days: int = 90) -> str:
    """MCRS 발생 장비의 PM 이력과 '발생 시점이 직전 PM 으로부터 며칠 뒤인지'를 조회한다.

    언제 사용: MCRS 원인이 장비 상태인지 확인할 때. PM 직후 발생이면 PM 작업 자체를,
    PM 주기를 한참 넘겨 발생했으면 PM 지연을 의심한다.

    다른 tool 과의 구분:
    - PM 을 기준으로 한 전후 데이터 비교까지 필요하면 compare_mcrs_pm_effect 를 사용한다.
      이 tool 은 PM 이 '언제 됐는지'만 알려준다.
    - 장비의 현재 상태(RUN/IDLE/DOWN)는 get_eq_status 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 90일.
    """
    data = pm.get_pm_history(lot_id, step_id, days)
    last = data["last_pm"]
    lines = [
        f"PM 이력 — 장비 {data['eq_id']} (최근 {data['days']}일, 정기 주기 약 {data['pm_cycle_days']}일)",
        f"MCRS 발생: {data['issue']['detected_at']}",
        f"직전 PM: {last['started_at']} ({last['pm_type']}, {last['main_work']})"
        f" → 발생까지 {data['days_since_last_pm']}일 경과",
        "",
        "전체 이력:",
    ]
    for rec in data["records"]:
        lines.append(
            f"  {rec['started_at']} | {rec['pm_type']} | {rec['main_work']}"
            f" | {rec['duration_h']}h | {rec['pm_id']}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------- 7. Trend

@tool
@safe_tool
def get_mcrs_step_trend(lot_id: str, step_id: str, days: int = 30) -> str:
    """MCRS 발생 공정의 최근 N일 검사 데이터를 일 단위로 조회한다 (trend 작성용).

    언제 사용: 이번 MCRS 가 갑자기 튄 것인지, 이전부터 서서히 나빠지고 있었는지
    확인할 때. 기본 30일.

    다른 tool 과의 구분:
    - PM 시점을 기준으로 구간을 나눈 비교가 필요하면 compare_mcrs_pm_effect 를 사용한다.
      이 tool 은 구간 구분 없이 날짜별 원본 추이만 준다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 30일.
    """
    data = pm.get_step_trend(lot_id, step_id, days)
    issue = data["issue"]
    s = data["summary"]
    lines = [
        f"{issue['step_id']} 최근 {data['days']}일 검사 추이 (device {issue['device_id']})",
        f"전체: n={s['count']}, 평균 {s['mean']}ea, 표준편차 {s['std']}, "
        f"범위 {s['min']}~{s['max']}ea",
        "",
        "date | mean_defect | n",
    ]
    for point in data["points"]:
        lines.append(f"{point['date']} | {point['mean_defect']:>6} | {point['sample_count']}")
    lines += ["", "위 데이터로 trend 차트를 그려 사용자에게 표시하세요."]
    return "\n".join(lines)


# ------------------------------------------------------- 8. PM 전후 비교

@tool
@safe_tool
def compare_mcrs_pm_effect(lot_id: str, step_id: str, days: int = 30) -> str:
    """직전 PM 시점을 기준으로 MCRS 발생 전후를 세 구간으로 나눠 통계 비교한다.

    구간: (1) PM 이전 = 기준선, (2) PM 이후~MCRS 발생 전 = PM 이 제대로 됐는지,
    (3) MCRS 발생 이후 = 지금도 계속 나쁜지.

    언제 사용: PM 이 원인인지 판단할 때. get_mcrs_pm_history 와 get_mcrs_step_trend 를
    각각 부른 뒤 직접 평균을 계산하지 말고 이 tool 을 사용한다 — 계산은 이 tool 이 한다.

    다른 tool 과의 구분:
    - PM 날짜만 필요하면 get_mcrs_pm_history, 날짜별 원본 추이만 필요하면
      get_mcrs_step_trend 를 사용한다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01).
        days: 비교에 사용할 데이터 기간(일). 기본 30일.
    """
    data = pm.compare_pm_effect(lot_id, step_id, days)
    last = data["last_pm"]
    labels = {
        "before_pm": "PM 이전 (기준선)",
        "after_pm_before_mcrs": "PM 이후~MCRS 발생 전",
        "after_mcrs": "MCRS 발생 이후",
    }
    lines = [
        f"PM 전후 비교 — 장비 {data['issue']['eq_id']} / {data['issue']['step_id']}",
        f"직전 PM: {last['started_at']} ({last['pm_type']}, {last['main_work']})",
        f"MCRS 발생: {data['detected_at']} (PM 후 {data['days_since_last_pm']}일, "
        f"정기 주기 {data['pm_cycle_days']}일)",
        "",
    ]
    for key, label in labels.items():
        w = data["windows"][key]
        if w["count"] == 0:
            lines.append(f"{label}: 해당 구간 데이터 없음")
        else:
            lines.append(
                f"{label}: n={w['count']}, 평균 {w['mean']}ea, 표준편차 {w['std']}, "
                f"범위 {w['min']}~{w['max']}ea"
            )
    lines += [
        "",
        "판정 가이드: PM 이후 구간이 PM 이전과 비슷하면 PM 자체는 정상 수행된 것이고, "
        "PM 이후 구간부터 나빠졌으면 PM 작업을 의심합니다. "
        "MCRS 이후 구간이 여전히 높으면 원인이 해소되지 않은 것입니다.",
    ]
    return "\n".join(lines)


# ------------------------------------------------- 9. 과거 INSP MAP 이어보기

@tool
@safe_tool
def get_insp_map_history(lot_id: str, step_id: str, slot_no: int | None = None) -> str:
    """같은 Lot/슬롯이 지나온 과거 검사 공정의 INSP MAP 을 오래된 순으로 조회한다.

    언제 사용: 해당 슬롯이 원래부터 나빴는지, 이번 공정에서 갑자기 나빠졌는지
    확인할 때. 결함 발생 공정을 좁히는 데 쓴다.

    다른 tool 과의 구분:
    - 현재 공정의 슬롯별 MAP 은 get_insp_map 을 사용한다 (같은 시점, 여러 슬롯).
      이 tool 은 같은 슬롯의 여러 시점이다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01). 이 공정 '이전' 이력을 찾는다.
        slot_no: 추적할 슬롯 번호. 생략하면 MCRS 발생 슬롯을 사용한다.
    """
    data = insp.get_insp_map_history(lot_id, step_id, slot_no)
    issue = data["issue"]
    lines = [
        f"INSP MAP 이력 — Lot {issue['lot_id']} / 슬롯 {data['slot_no']} (오래된 순)",
        "",
        "step | 검사시각 | 장비 | defect | image",
    ]
    for item in data["timeline"]:
        mark = " ★MCRS" if item.get("is_mcrs_step") else ""
        lines.append(
            f"{item['step_id']} ({item['step_desc']}) | {item['inspected_at']}"
            f" | {item['eq_id']} | {item['defect_count']}ea{mark} | {item['image_url']}"
        )
    if len(data["timeline"]) == 1:
        lines += ["", "주의: 이 공정 이전의 검사 이력이 없어 비교 대상이 없습니다."]
    else:
        lines += ["", "위 MAP 들을 시간 순으로 나란히 표시해 결함 증가 시점을 보여주세요."]
    return "\n".join(lines)


# ----------------------------------------------- 10. 장비 기준 교차 확인

@tool
@safe_tool
def get_eq_insp_coverage(lot_id: str, step_id: str, days: int = 30) -> str:
    """MCRS 발생 장비를 지나간 '다른 device / 다른 공정' 의 검사 실적을 조회한다.

    언제 사용: 장비 자체의 문제인지, 이 device/공정 조합에만 나타나는 문제인지
    가를 때. 다른 device 도 같이 나쁘면 장비 이슈, 이 조합만 나쁘면 공정/제품 이슈다.

    다른 tool 과의 구분:
    - 같은 Lot 안의 다른 슬롯 비교는 get_insp_map 이다. 이 tool 은 같은 장비를
      지나간 **다른 Lot/device** 를 본다.

    Args:
        lot_id: Lot 번호 (예: TE2FE35).
        step_id: 사용자가 고른 공정 ID (예: INSP-CMP-01).
        days: 조회할 기간(일). 기본 30일.
    """
    data = insp.get_eq_insp_coverage(lot_id, step_id, days)
    issue = data["issue"]
    lines = [
        f"장비 {issue['eq_id']} 교차 확인 — 최근 {data['days']}일, "
        f"MCRS 조합({issue['device_id']}/{issue['step_id']}) 제외",
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


register(get_mcrs_issues)
register(get_insp_map)
register(get_mcrs_review_images)
register(get_mcrs_pm_history)
register(get_mcrs_step_trend)
register(compare_mcrs_pm_effect)
register(get_insp_map_history)
register(get_eq_insp_coverage)
