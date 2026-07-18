# 씨리아 (Siria) — 반도체 라인 업무 LLM Agent

LangGraph 기반 RAG + Tool Calling ReAct agent. tool 조합과 시스템 프롬프트만
바꿔 여러 agent 를 찍어낼 수 있는 factory 구조.

## 아키텍처 원칙

1. **비즈니스 로직과 인터페이스 분리** — DB 조회/검증/쿼리 로직은 `core/` 에만
   존재한다. `tools/` 의 LangGraph tool 은 core 를 호출하는 얇은 wrapper 다.
   같은 core 함수를 나중에 MCP 서버, langflow 컴포넌트(`adapters/`)로도 노출한다.
2. **수작업 JSON 스키마 금지** — `@tool` 데코레이터 + type hint + docstring 으로
   스키마가 자동 생성된다.
3. **Registry 기반 조합** — tool 은 `tools/registry.py` 에 이름으로 등록되고,
   agent 는 yaml 에 적힌 이름 목록으로 조합된다.
4. **RAG 도 tool** — 항상 검색하지 않고 `search_knowledge` tool 로 등록해 LLM 이
   필요할 때만 호출한다.

## 디렉토리 구조

```
siria/
├── config.py              # 환경변수 기반 설정 (LLM/DB/Milvus/Phoenix) — TODO 채우기
├── observability.py       # Phoenix tracing (SIRIA_PHOENIX_ENABLED 로 on/off)
├── core/                  # 순수 비즈니스 로직 (프레임워크 의존 없음)
│   ├── errors.py          # ToolError — LLM 에게 보여줄 한국어 안내 예외
│   ├── db.py              # DB 커넥션 (TODO)
│   ├── lot_service.py     # ✅ mock 구현 예시
│   ├── knowledge_service.py  # ✅ mock 구현 예시 (Milvus RAG)
│   └── eq/wip/hold/part_service.py  # 스텁
├── tools/
│   ├── common.py          # safe_tool 에러 처리 데코레이터
│   ├── registry.py        # 이름 → tool 매핑, get_tools()
│   ├── lot_tools.py       # ✅ 완전한 예시 (get_lot_info)
│   ├── knowledge_tools.py # ✅ 완전한 예시 (search_knowledge)
│   └── eq/wip/hold/part_tools.py  # 동일 패턴 스텁
├── agents/
│   ├── factory.py         # yaml → create_react_agent
│   └── configs/           # line_agent.yaml, trouble_lot_agent.yaml
├── adapters/              # 확장용 자리 (MCP, langflow) — 스텁만
└── app/main.py            # FastAPI 진입점
```

## 실행

```bash
cd siria
pip install -r requirements.txt

# 내부망 정보 설정 (config.py 의 TODO 항목)
export SIRIA_LLM_BASE_URL=http://<내부 LLM 엔드포인트>/v1
export SIRIA_LLM_MODEL=<모델명>

uvicorn app.main:app --reload
# POST /chat {"message": "LOT2401A001 상태 알려줘", "agent": "line_agent"}
# GET  /agents  — agent 목록
# GET  /tools   — 등록된 tool 목록
```

## 새 tool 추가하는 방법

1. **core 에 로직 작성** — `core/xxx_service.py` 에 순수 함수로 구현한다.
   입력 오류·미존재 데이터는 `raise ToolError("조회 실패: ...")` 로 LLM 이
   다음 행동을 판단할 수 있는 한국어 메시지를 던진다.
2. **tool wrapper 작성** — `tools/xxx_tools.py` 에서:
   ```python
   @tool
   @safe_tool            # 순서 중요: @tool 안쪽에 있어야 스키마 생성이 안 깨짐
   def my_tool(arg: str) -> str:
       """<무엇을 조회하는지 한 줄>.

       언제 사용: <이 tool 을 써야 하는 상황>.

       다른 tool 과의 구분:
       - <헷갈리기 쉬운 tool 과의 차이>.

       Args:
           arg: <설명 + 예시>.
       """
       return format(xxx_service.my_func(arg))

   register(my_tool)
   ```
   docstring 세 요소(무엇을 / 언제 / 다른 tool 과 구분)는 필수 — 이게 그대로
   LLM 의 tool 선택 기준이 된다.
3. **registry 에 모듈 등록** — 새 파일이면 `tools/registry.py` 의
   `_TOOL_MODULES` 에 `"tools.xxx_tools"` 한 줄 추가.
4. **agent 에 포함** — 쓰고 싶은 agent yaml 의 `tools:` 목록에 이름 추가.

## 새 agent 찍어내는 방법

1. `agents/configs/my_agent.yaml` 생성:
   ```yaml
   name: my_agent
   recursion_limit: 15        # ReAct 루프 안전장치 (생략 시 기본값)
   tools:
     - get_lot_info
     - search_knowledge
   system_prompt: |
     당신은 ... '씨리아'입니다.
     ...
   ```
2. 끝. 코드 수정 없이 바로 사용 가능:
   ```python
   from agents.factory import create_agent
   agent = create_agent("my_agent")
   result = agent.invoke("질문")
   ```
   API 로는 `POST /chat` 의 `"agent": "my_agent"` 로 지정한다.

## 에러 처리 규칙

- core 는 예상 가능한 실패(형식 오류, 데이터 없음)에 `ToolError` 를 던진다.
- `safe_tool` 데코레이터가 모든 tool 에서:
  - `ToolError` → 메시지를 그대로 LLM 에 반환
  - 그 외 예외 → traceback 은 서버 로그에만 남기고, LLM 에는 재시도 중단을
    유도하는 일반 안내문 반환
- raw exception 을 LLM 에 그대로 노출하지 않는다.

## 가이아2.0 연동 설계 (예정)

가이아2.0 은 agent 선택(라우팅)을 담당하는 사내 플랫폼이다. 씨리아를 노출하는
방식은 두 가지가 있고, **둘 다 같은 core 위에서 어댑터로 공존 가능**하다.

| | 완성품 (agent 경유) | 스킬카드 직접 등록 |
|---|---|---|
| 실행 경로 | 가이아 → 씨리아 agent(ReAct 루프) → core | 가이아 LLM → tool 호출 → core |
| tool 선택 주체 | 씨리아 LLM (시스템 프롬프트 통제 가능) | 가이아 LLM (docstring 이 유일한 통제 수단) |
| 씨리아의 역할 | 답변까지 생성 | data 조회만 |
| 유리한 업무 | 다단계 분석 (예: trouble lot — 조회 순서 노하우가 프롬프트에 있음) | 단발 조회 (빠르고 LLM 비용 절감) |

- 현재 회사 구조: 완성품 방식 (가이아는 agent 선택만, tool 선택은 씨리아 내부).
- 스킬카드 단독 등록(씨리아 agent 미경유) 가능 여부는 확인 중.
- 스킬카드는 인터페이스(이름/설명/파라미터/호출 주소)만 등록하는 것이고,
  core 로직은 카드에 포함되는 게 아니라 카드가 가리키는 서버에 배포된다.
- 프로토콜이 MCP 면 `adapters/mcp_server.py`, REST 면 어댑터 파일 하나 추가로
  대응한다. 어느 쪽이든 core/tools 는 수정 없음.
- 개별 tool 대신 씨리아 agent 전체를 tool 하나(`ask_siria(question)`)로 노출하는
  절충안도 가능 — tool 선택 로직을 우리가 통제하고 싶을 때 사용.

## Observability

`SIRIA_PHOENIX_ENABLED=true` + `SIRIA_PHOENIX_ENDPOINT=<collector 주소>` 설정 시
Phoenix(Arize) tracing 이 활성화된다. 미설정이면 조용히 꺼진다.
