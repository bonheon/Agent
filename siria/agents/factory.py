"""Agent Factory.

agents/configs/*.yaml 에 tool 목록 + 시스템 프롬프트를 정의하면
create_react_agent 로 agent 를 생성한다. tool 조합과 프롬프트만 바꿔
여러 agent 를 찍어내는 것이 목적.

사용 예:
    from agents.factory import create_agent

    agent = create_agent("line_agent")
    result = agent.invoke("LOT2401A001 지금 어디 있어?")
    print(result["messages"][-1].content)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from langgraph.prebuilt import create_react_agent

from config import get_llm, settings
from skills.loader import SKILLS_DIR, load_skill
from tools.registry import get_tools

CONFIG_DIR = Path(__file__).parent / "configs"


@dataclass
class AgentConfig:
    """yaml 한 파일 = agent 하나의 정의."""

    name: str
    system_prompt: str
    tools: list[str]
    # ReAct 루프 안전장치: 무한 tool call 루프 방지
    recursion_limit: int = settings.default_recursion_limit

    @classmethod
    def from_yaml(cls, path: Path) -> "AgentConfig":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        # skill: <name> 을 쓰면 tools/system_prompt 를 skills/<name>/SKILL.md 에서
        # 가져온다. 절차 문서가 단일 원본이 되도록 yaml 에 복붙하지 않는다.
        # yaml 에 같은 키를 직접 쓰면 그쪽이 우선한다 (부분 override 용).
        skill_name = data.pop("skill", None)
        if skill_name:
            skill = load_skill(skill_name)
            data.setdefault("name", skill.name)
            data.setdefault("tools", skill.tools)
            data.setdefault("system_prompt", skill.system_prompt)

        required = {"name", "system_prompt", "tools"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"{path.name} 에 필수 항목 누락: {sorted(missing)}")
        return cls(**data)


class SiriaAgent:
    """create_react_agent 결과를 감싸 recursion_limit 을 항상 적용하는 래퍼."""

    def __init__(self, graph, config: AgentConfig):
        self.graph = graph
        self.config = config

    def _runtime_config(self) -> dict:
        return {"recursion_limit": self.config.recursion_limit}

    def invoke(self, user_input: str) -> dict:
        return self.graph.invoke(
            {"messages": [("user", user_input)]}, config=self._runtime_config()
        )

    def stream(self, user_input: str):
        """토큰/스텝 단위 스트리밍이 필요하면 이걸 사용 (FastAPI SSE 등)."""
        return self.graph.stream(
            {"messages": [("user", user_input)]},
            config=self._runtime_config(),
            stream_mode="values",
        )


def agent_config_paths() -> dict[str, Path]:
    """agent 이름 → 정의 파일 경로.

    두 곳에서 모은다:
    - agents/configs/<name>.yaml — 여러 skill/tool 을 조합하는 범용 agent
    - skills/<name>/agent.yaml   — skill 이 자기 실행 설정을 함께 들고 다니는 경우.
      skill 폴더를 지우면 agent 정의도 같이 사라져야 dangling config 가 안 생긴다.
    """
    paths = {p.stem: p for p in CONFIG_DIR.glob("*.yaml")}
    for path in sorted(SKILLS_DIR.glob("*/agent.yaml")):
        name = path.parent.name
        if name in paths:
            raise ValueError(
                f"agent 이름 중복: '{name}' — {paths[name]} 와 {path} 가 충돌합니다."
            )
        paths[name] = path
    return paths


def load_agent_config(name: str) -> AgentConfig:
    paths = agent_config_paths()
    path = paths.get(name)
    if path is None:
        raise FileNotFoundError(
            f"agent 정의 없음: '{name}'. 사용 가능한 agent: {sorted(paths)}"
        )
    return AgentConfig.from_yaml(path)


def create_agent(name: str, llm=None) -> SiriaAgent:
    """configs/<name>.yaml 정의로 ReAct agent 를 생성한다.

    llm 을 넘기지 않으면 config.get_llm() 의 기본 LLM 을 사용한다.
    """
    cfg = load_agent_config(name)
    graph = create_react_agent(
        llm or get_llm(),
        tools=get_tools(cfg.tools),
        prompt=cfg.system_prompt,
    )
    return SiriaAgent(graph, cfg)
