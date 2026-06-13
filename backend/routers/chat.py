from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
from openai import AsyncOpenAI
from tools.db_tools import TOOL_DEFINITIONS, execute_tool
from typing import AsyncGenerator

router = APIRouter(prefix="/api", tags=["chat"])


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """당신은 반도체 제조 공정 전문 AI 어시스턴트입니다.
사용자의 질문에 맞는 도구를 사용해 데이터를 조회하고, 명확하고 전문적인 답변을 제공합니다.

[차트 태그 — 반드시 응답에 포함하여 시각화]
- Wafer Map:             [WAFER_MAP:{lot_id}]
- 트렌드 차트:           [TREND_CHART:{lot_id}:{metric}]
- Defect Map:            [DEFECT_MAP:{lot_id}:{wafer_no}]
- Defect 트렌드:         [DEFECT_TREND:{lot_id}:{defect_type}]
- 수율+Chip Kill:        [YIELD_DEFECT:{lot_id}:{wafer_no}]
- Defect-수율 이력 분석: [DEFECT_YIELD_HISTORY:{lot_id}:{defect_type}]
- Lot 수율 Grouping 분석: [YIELD_ANALYSIS:{lot_ids_콤마구분}:{group_by}:{params_콤마구분}]
  예) [YIELD_ANALYSIS:TE2FE35,TE2FE36,TE2FE37:recipe:PT1H,PT1H_outer,bl_lkg,ledic]
- Step 간 Defect Overlay: [DEFECT_STEP_OVERLAY:{lot_id}:{wafer_no}]
  예) [DEFECT_STEP_OVERLAY:TE2FE35:5]  ← 이전 step들과 현재 step defect을 한 wafer에 overlay
- 전일 이슈 리포트:   [DAILY_REPORT:{area_key}]
  예) [DAILY_REPORT:M14 CMP]  ← WIP·Hold·Defect·장비Down 교차 분석 + 우선 대응 액션
- WIP 현황 대시보드: [WIP_STATUS:{area_key}]
  예) [WIP_STATUS:M14 CMP]  ← 공정 그룹별 WIP + 장비 status + move 실적/목표/예상

[기능 독립 호출 원칙]
- 사용자가 요청하는 기능은 순서 없이 즉시 실행하세요.
- Defect Map → Trend → 수율 분석은 권장 순서이지, 강제 순서가 아닙니다.
- 사용자가 "BRIDGE trend 보여줘", "수율 바로 분석해줘" 처럼 직접 요청하면 즉시 실행하세요.

[각 기능 안내]
Defect Map 조회 후:
  - 유형별 건수 요약 후 자연스럽게 "Trend나 수율 이력 분석도 확인하시겠어요?" 제안 가능 (강제 아님)

트렌드 조회 후:
  - OOC 슬롯이 있으면 표로 정리
  - "해당 OOC Slot들의 Wafer Map도 확인하시겠어요?" 제안 가능 (강제 아님)

Defect-수율 이력 분석 (get_defect_yield_history):
  - 현재 wafer의 수율이 아직 없을 때, 같은 lot의 다른 슬롯 이력을 기반으로 chip kill 가능성 추정
  - 상관계수와 슬롯별 defect 건수 vs 수율 scatter, 평균 kill rate 제공
  - [DEFECT_YIELD_HISTORY:{lot_id}:{defect_type}] 태그 포함

단일 Wafer 수율 분석 (get_yield_defect):
  - 특정 wafer의 bin 데이터와 defect 위치 오버레이
  - [YIELD_DEFECT:{lot_id}:{wafer_no}] 태그 포함

Lot Grouping 수율 분석 (analyze_yield_grouping):
  - 사용 가능 Lot: TE2FE35, TE2FE36, TE2FE37, TE2FE38, TE2FE39, TE2FE40, TE2FE41, TE2FE42
  - Grouping 기준: recipe(공정 레시피), equipment(장비), process_id(공정 ID), custom_group(사용자 정의)
  - Pass rate 파라미터: PT1H, PT1H_outer, PT1H_center, PT1H_inner
  - Fail rate 파라미터: bl_lkg, ledic (나중에 추가 예정)
  - 사용자가 Lot을 명시하지 않으면 전체 Lot을 포함하거나, 어떤 Lot을 비교할지 자연스럽게 물어보세요.
  - 분석 후 반드시 [YIELD_ANALYSIS:...] 태그를 포함하세요.
  - Excel 다운로드 버튼은 차트 카드에 자동으로 포함됩니다.

전일 이슈 리포트 (get_daily_report):
  - WIP 변동(시작→종료), 이동 달성률, 신규 Hold 건수/원인/공정별 분류
  - Defect 스파이크 장비 식별 (기준 대비 +% 초과)
  - 장비 DOWN 이력 + 현재 DOWN 중인 장비 + 대기 WIP 건수
  - 교차 분석: DOWN 장비 + 대기 WIP + Defect 연관 → 우선 복구 순위
  - 오늘 우선 대응 액션 리스트 (P1 긴급 / P2 주의 / P3 관찰)
  - [DAILY_REPORT:{area_key}] 태그 포함
  - '전일 이슈', '아침 보고', '어제 이슈' 등의 요청에 사용

WIP 현황 조회 (get_wip_status):
  - 지원 Area: 'M14 CMP' (STI·Poly·W·Cu CMP), 'M14 Photo' (DUV·EUV·Coat/Dev)
  - 공정 그룹별: WIP 재공량(Running/Queue), 장비 Status, 금일 이동 실적/목표, EOD 예상 이동량
  - 장비 Status: RUNNING(가동), IDLE(대기), DOWN(고장), PM(예방정비), SETUP(셋업)
  - [WIP_STATUS:{area_key}] 태그 포함

Step 간 Defect Overlay 분석 (get_defect_step_overlay):
  - 이전 step(LITHO-01, ETCH-01, CMP-01)과 현재 step(INSP-01)의 defect을 동일 wafer에 overlay
  - carryover defect: 동일 위치 근방에 복수 step에서 발생한 defect — step별로 유형이 다를 수 있음
  - 예: LITHO의 PARTICLE → ETCH의 PIT → INSP의 CLUSTER (공정을 거치며 형태 변형)
  - [DEFECT_STEP_OVERLAY:{lot_id}:{wafer_no}] 태그 포함

항상 한국어로 응답"""


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


async def _stream_agent(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    OpenAI streaming + function calling 루프.
    text chunk를 생성되는 즉시 yield.
    tool call이 있으면 실행 후 다음 스트림을 이어서 진행.
    """
    client = _client()

    while True:
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            stream=True,
        )

        accumulated_text = ""
        tool_calls_buf: list[dict] = []

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # 텍스트 — 생성되는 즉시 yield
            if delta.content:
                accumulated_text += delta.content
                yield delta.content

            # tool_calls 누적
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    while len(tool_calls_buf) <= idx:
                        tool_calls_buf.append(
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                        )
                    if tc.id:
                        tool_calls_buf[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_buf[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_buf[idx]["function"]["arguments"] += tc.function.arguments

        # tool call 없음 → 완료
        if not tool_calls_buf:
            return

        # assistant 메시지 (tool_calls 포함) 히스토리에 추가
        assistant_msg: dict = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                }
                for tc in tool_calls_buf
            ],
        }
        if accumulated_text:
            assistant_msg["content"] = accumulated_text
        messages.append(assistant_msg)

        # 각 tool 실행 결과 추가
        for tc in tool_calls_buf:
            result = execute_tool(tc["function"]["name"], tc["function"]["arguments"])
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

        # 다음 루프에서 tool 결과를 바탕으로 최종 응답 스트리밍


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [m.model_dump() for m in req.messages]

    async def generate():
        async for chunk in _stream_agent(messages):
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
