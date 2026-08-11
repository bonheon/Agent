"""SKILL.md 로더.

skill 하나 = 디렉토리 하나 = `skills/<name>/SKILL.md` 파일 하나.

    ---
    name: mcrs_analysis
    description: |
      이 skill 을 언제 쓰는지 (라우팅 판단 근거)
    tools:
      - get_mcrs_issues
      - ...
    ---

    # 절차 본문 (그대로 system prompt 가 된다)

frontmatter 는 "이 skill 이 무엇인지"(외부 플랫폼에 등록할 메타데이터), 본문은
"어떤 순서로 어떻게 판단하는지"(절차)다. 절차를 코드가 아니라 문서로 두는 이유는,
가이아2.0 처럼 우리 코드를 import 하지 않는 플랫폼에도 본문만 그대로 넘길 수 있게
하기 위해서다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).parent


@dataclass
class Skill:
    name: str
    description: str
    tools: list[str]
    system_prompt: str
    path: Path = field(compare=False, repr=False, default=SKILLS_DIR)


def _split_frontmatter(text: str, path: Path) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError(f"{path}: SKILL.md 는 '---' 로 시작하는 frontmatter 가 필요합니다.")

    # 첫 줄의 '---' 이후에서 닫는 '---' 을 찾는다.
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        raise ValueError(f"{path}: frontmatter 를 닫는 '---' 이 없습니다.")

    meta = yaml.safe_load(parts[0].lstrip("-\n")) or {}
    body = parts[1].lstrip("\n")
    return meta, body


def load_skill(name: str) -> Skill:
    """skills/<name>/SKILL.md 를 읽어 Skill 로 반환한다."""
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(
            f"skill 정의 없음: {path}. 사용 가능한 skill: {list_skills()}"
        )

    meta, body = _split_frontmatter(path.read_text(encoding="utf-8"), path)

    missing = {"name", "description", "tools"} - meta.keys()
    if missing:
        raise ValueError(f"{path}: frontmatter 필수 항목 누락: {sorted(missing)}")
    if not body.strip():
        raise ValueError(f"{path}: 절차 본문이 비어 있습니다.")

    return Skill(
        name=meta["name"],
        description=meta["description"].strip(),
        tools=list(meta["tools"]),
        system_prompt=body.strip(),
        path=path,
    )


def list_skills() -> list[str]:
    """정의된 skill 이름 목록."""
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
