"""Tool Registry: 이름 → tool 매핑.

각 tools/*_tools.py 모듈은 @tool 로 만든 tool 을 register() 로 등록하고,
agent factory 는 get_tools([...]) 로 원하는 조합만 꺼내 agent 를 구성한다.

tool 이 등록되는 경로는 두 가지다:
1. 공용 tool — tools/*_tools.py. 새 파일을 만들면 _TOOL_MODULES 에 한 줄 추가.
2. skill 전용 tool — skills/<name>/tools.py. **자동으로 발견되므로 등록 불필요.**
   skill 폴더 하나가 배포 단위이므로, 폴더를 넣고 빼는 것만으로 tool 이 붙고 떨어져야 한다.
"""
import importlib
from pathlib import Path

from langchain_core.tools import BaseTool

_REGISTRY: dict[str, BaseTool] = {}
_loaded = False

# 여러 skill/agent 가 공유하는 tool. 새 tool 파일 추가 시 여기에 한 줄 추가.
_TOOL_MODULES = [
    "tools.lot_tools",
    "tools.eq_tools",
    "tools.wip_tools",
    "tools.hold_tools",
    "tools.part_tools",
    "tools.knowledge_tools",
]

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def register(tool: BaseTool) -> BaseTool:
    """tool 을 registry 에 등록한다. 각 *_tools.py 모듈 하단에서 호출."""
    if tool.name in _REGISTRY:
        raise ValueError(f"tool 이름 중복: '{tool.name}' (이미 등록됨)")
    _REGISTRY[tool.name] = tool
    return tool


def _skill_tool_modules() -> list[str]:
    """skills/<name>/tools.py 를 전부 찾아 모듈 경로로 반환한다."""
    return sorted(
        f"skills.{p.parent.name}.tools" for p in _SKILLS_DIR.glob("*/tools.py")
    )


def _load_all() -> None:
    """모든 tool 모듈을 import 해서 register() 가 실행되게 한다."""
    global _loaded
    if _loaded:
        return
    for module in _TOOL_MODULES + _skill_tool_modules():
        importlib.import_module(module)
    _loaded = True


def get_tools(names: list[str]) -> list[BaseTool]:
    """이름 목록으로 tool 조합을 꺼낸다. 없는 이름이면 사용 가능 목록과 함께 에러."""
    _load_all()
    missing = [n for n in names if n not in _REGISTRY]
    if missing:
        raise KeyError(
            f"등록되지 않은 tool: {missing}. 사용 가능한 tool: {sorted(_REGISTRY)}"
        )
    return [_REGISTRY[n] for n in names]


def all_tools() -> list[BaseTool]:
    """등록된 전체 tool (등록 순서). MCP 서버가 통째로 노출할 때 사용."""
    _load_all()
    return list(_REGISTRY.values())


def list_tools() -> dict[str, str]:
    """등록된 전체 tool 의 {이름: 설명 첫 줄} 목록. 디버깅/문서용."""
    _load_all()
    return {
        name: (t.description or "").strip().splitlines()[0]
        for name, t in sorted(_REGISTRY.items())
    }
