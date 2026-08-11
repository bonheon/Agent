"""MCRS 분석 skill.

이 폴더 하나가 skill 하나의 배포 단위다:

    SKILL.md      절차와 판단 기준 (외부 플랫폼에 넘길 본문)
    tools.py      LangGraph tool 8개 — services 를 호출하는 얇은 wrapper
    services/     순수 비즈니스 로직 (프레임워크 의존 없음)

이 skill 을 떼어내려면 이 폴더만 옮기면 된다. 폴더 밖에 대한 의존은
공용 인프라 3개뿐이다: core.errors.ToolError, tools.common.safe_tool,
tools.registry.register.
"""
