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
├── core/                  # 여러 skill 이 공유하는 순수 비즈니스 로직
│   ├── errors.py          # ToolError — LLM 에게 보여줄 한국어 안내 예외
│   ├── db.py              # DB 커넥션 (TODO)
│   ├── lot_service.py     # ✅ mock 구현 예시
│   ├── knowledge_service.py  # ✅ mock 구현 예시 (Milvus RAG)
│   └── eq/wip/hold/part_service.py  # 스텁
├── tools/                 # 여러 skill 이 공유하는 tool
│   ├── common.py          # safe_tool 에러 처리 데코레이터
│   ├── registry.py        # 이름 → tool 매핑, get_tools() + skill tool 자동 발견
│   ├── lot_tools.py       # ✅ 완전한 예시 (get_lot_info)
│   ├── knowledge_tools.py # ✅ 완전한 예시 (search_knowledge)
│   └── eq/wip/hold/part_tools.py  # 동일 패턴 스텁
├── skills/                # skill = 폴더 1개 = 배포·삭제 단위
│   ├── loader.py          # SKILL.md 파서 (frontmatter + 본문)
│   └── mcrs_analysis/     # ✅ MCRS 분석 skill (완전한 예시)
│       ├── SKILL.md       #    절차 10단계 + 판단 기준 (외부에 넘길 본문)
│       ├── agent.yaml     #    이 skill 을 단독 실행할 때의 agent 설정
│       ├── tools.py       #    tool 8개 — services 를 부르는 얇은 wrapper
│       └── services/      #    순수 로직 (context/mcrs/insp/review/pm)
├── agents/
│   ├── factory.py         # yaml → create_react_agent
│   └── configs/           # 여러 skill 을 조합하는 범용 agent 설정
├── adapters/
│   ├── mcp_server.py                  # ✅ 동작하는 예제 (get_lot_info 를 MCP tool 로 노출)
│   ├── mcp_client_example.py          # ✅ 위 서버를 호출해보는 raw MCP client 예제
│   ├── mcp_langgraph_agent_example.py # ✅ 다른 LangGraph agent 가 이 tool 을 붙여 쓰는 예제
│   └── langflow/                      # 확장용 자리 — 스텁만
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

먼저 **어디에 둘지** 정한다. 한 skill 에서만 쓰면 `skills/<name>/` 안에,
여러 skill/agent 가 공유하면 `core/` + `tools/` 에 둔다. 아래는 공유 tool 기준이고,
skill 전용이면 경로만 `skills/<name>/services/` 와 `skills/<name>/tools.py` 로 바꾼다.

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
   (skill 전용 tool 은 `skills/<name>/tools.py` 가 자동 발견되므로 이 단계가 없다)
4. **agent 에 포함** — 쓰고 싶은 agent yaml 또는 SKILL.md 의 `tools:` 목록에 이름 추가.

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

## Skill — 다단계 업무를 절차 문서로 분리

tool 하나로 끝나지 않고 **정해진 순서 + 중간에 사용자 선택**이 필요한 업무는
skill 로 만든다. **폴더 하나가 skill 하나이자 배포·삭제 단위다.**

```
skills/mcrs_analysis/
├── SKILL.md      # 절차 + 등록용 메타데이터
├── agent.yaml    # 이 skill 단독 실행 설정 (선택)
├── tools.py      # @tool 8개 — 자동으로 registry 에 등록된다
└── services/     # 순수 로직 (프레임워크 의존 없음)
```

폴더 밖으로 나가는 의존은 공용 인프라 3개뿐이다 — `core.errors.ToolError`,
`tools.common.safe_tool`, `tools.registry.register`. 그래서 **폴더를 넣으면 tool 과
agent 가 붙고, 폴더를 빼면 같이 사라진다.** 등록 목록을 따로 고칠 필요가 없고,
남은 설정이 dangling 으로 남지도 않는다.

여러 skill 이 함께 쓰는 로직만 `core/` 와 `tools/` 로 올린다. 한 skill 만 쓰는
로직을 거기 두면 skill 을 떼어낼 때 무엇이 딸려가야 하는지 알 수 없게 된다.

`SKILL.md` 구조:

```
---
name: mcrs_analysis
description: |
  이 skill 을 언제 쓰는지 — 외부 플랫폼의 라우팅 판단 근거가 된다.
tools:
  - get_mcrs_issues        # registry 에 등록된 tool 이름
  - ...
---

# 절차 본문 — 그대로 system prompt 가 된다
```

**tool 과 skill 의 경계:**

| | tool | skill |
|---|---|---|
| 정체 | 함수 1개 = 조회 1건 | 문서 1개 = 조회 순서와 판단 기준 |
| 담는 것 | 쿼리·계산 | "먼저 A 조회 → 사용자에게 물음 → 답에 따라 B" |
| 못 담는 것 | 사용자에게 되묻고 기다리기 | 데이터 접근 |

사용자 선택 분기, 조회 순서, 결과 해석 기준은 **함수로 만들 수 없으므로** 전부
SKILL.md 본문에 들어간다. 반대로 평균·표준편차 같은 계산은 프롬프트에 맡기지 말고
tool 로 내린다 (LLM 이 원본 데이터를 놓고 암산하면 토큰만 쓰고 값도 틀린다).

**agent 에 연결:** yaml 에 `skill:` 한 줄만 쓰면 tools/system_prompt 를 SKILL.md 에서
가져온다. 절차를 yaml 에 복붙하지 않는다 — 원본은 SKILL.md 하나다.

```yaml
# skills/mcrs_analysis/agent.yaml → agent 이름은 폴더명(mcrs_analysis)
skill: mcrs_analysis
recursion_limit: 25
```

`POST /chat {"message": "...", "agent": "mcrs_analysis"}` 로 실행한다.
여러 skill 을 조합하는 범용 agent 는 지금처럼 `agents/configs/` 에 둔다.

**외부 노출:** `GET /skills` 로 등록용 메타데이터(이름/설명/tool 목록)를,
`GET /skills/{name}` 으로 절차 본문까지 받을 수 있다. 가이아2.0 처럼 씨리아 코드를
import 하지 않는 플랫폼에 skill 을 등록할 때 이 두 엔드포인트를 쓴다. 이때 넘어가는
것은 **인터페이스와 절차 본문뿐이고, 코드는 우리 서버에 그대로 남는다** — 폴더를
한 덩어리로 유지하는 이유는 업로드가 아니라 우리 쪽 배포·버전 관리 단위이기 때문이다.

### tool 인자 설계 원칙 — 앵커 인자만 받는다

`mcrs_analysis` 의 tool 9개는 전부 `(lot_id, step_id)` 만 받는다. 장비 ID·슬롯 번호·
device 는 `services/context.py` 의 `resolve_context()` 가 **공정 이력에서** 되찾는다.

LLM 에게 `eq_id` 를 넘기라고 하면 **아직 조회하지 않은 값을 지어내서** 넘긴다.
사용자가 실제로 고르는 값(여기서는 Lot 과 공정)만 인자로 받고 나머지는 서버가
유도하면, 잘못된 인자로 엉뚱한 데이터를 조회하는 경로 자체가 사라진다.

### 조회 계층과 분석 계층을 나눈다

같은 tool 세트가 "INSP 결과 보여줘" 같은 단발 질문과 "MCRS 원인 분석해줘" 같은
다단계 요청을 모두 받는다. 그러려면 두 가지를 지켜야 한다.

**1. 특수 상황을 전제조건으로 만들지 않는다.** 처음에는 모든 tool 이 MCRS 이슈
레코드에서 장비를 찾았고, 그래서 MCRS 가 없는 Lot 은 INSP 조회조차 막혔다. Lot 이
그 공정을 지나갔으면 장비는 공정 이력에 **항상** 있으므로, 컨텍스트 해결의 근거를
공정 이력으로 옮기고 MCRS 는 보강 정보로 얹었다. 없는 정보 때문에 실패하지 말고,
없는 대로 답하고 없다고 표시한다. `ToolError` 는 입력이 잘못됐을 때만 쓴다.

**2. 절차서에 경우의 수를 나열하지 않는다.** 단발 질문의 형태는 무한하므로 SKILL.md
에 열거할 수 없다. 대신 탈출 조항 한 줄("특정 데이터 하나만 요청하면 해당 tool 만
호출하고 끝낸다. 아래 절차는 원인 분석 요청일 때만 적용한다")을 맨 앞에 두고, tool
선택 자체는 docstring 에 맡긴다. 절차서는 **여러 tool 을 엮을 때의 순서와 판단 기준**
만 담당한다. 역할을 섞으면 프롬프트가 무한히 길어진다.

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

### MCP 예제 실행해보기

`adapters/mcp_server.py` 는 `core.lot_service.get_lot_info` 를 MCP tool 로
노출하는 동작하는 예제다. LangGraph tool(`tools/lot_tools.py`)과 같은 core
함수를 호출하지만, 같은 프로세스 함수 호출이 아니라 프로세스 경계를 넘는
MCP 프로토콜(stdio)로 호출된다는 점이 핵심 차이다 — 그래서 가이아2.0처럼
씨리아 코드를 import 하지 않는 외부 시스템도 tool 을 쓸 수 있다.

```bash
cd siria
pip install "mcp[cli]"

# 방법 1: 웹 inspector 로 tool 목록/스키마를 눈으로 확인하며 직접 호출
mcp dev adapters/mcp_server.py

# 방법 2: client 예제 스크립트로 전체 흐름(목록 조회 → 정상 호출 → 에러 호출) 실행
python -m adapters.mcp_client_example
```

### "다른 agent 에서 이 MCP tool 쓰기" 예제

씨리아 코드를 import 하지 않는 **별도의 LangGraph agent**가 이 MCP 서버의
tool 을 자기 tool 목록에 끼워 넣는 흐름은 `langchain-mcp-adapters` 로
확인할 수 있다. `MultiServerMCPClient.get_tools()` 가 돌려주는 tool 은
`tools/registry.py` 의 `get_tools([...])` 와 타입이 완전히 같은
`BaseTool` 이라, `create_react_agent(llm, tools=..., prompt=...)` 에
그대로 넣을 수 있다 — tool 출처만 로컬 import 대신 MCP 서버로 바뀔 뿐이다.

```bash
pip install "mcp[cli]" langchain-mcp-adapters langgraph langchain-openai
python -m adapters.mcp_langgraph_agent_example
```

LLM 엔드포인트(`SIRIA_LLM_BASE_URL`)가 아직 미설정이어도 tool 로딩과 직접
호출(`tool.ainvoke(...)`)까지는 확인 가능하고, agent 실행 단계만 건너뛴다.

## Observability

`SIRIA_PHOENIX_ENABLED=true` + `SIRIA_PHOENIX_ENDPOINT=<collector 주소>` 설정 시
Phoenix(Arize) tracing 이 활성화된다. 미설정이면 조용히 꺼진다.
