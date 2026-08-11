"""MCRS 분석 skill 의 비즈니스 로직.

순수 파이썬 — LangChain/LangGraph 의존이 없다. 같은 함수를 LangGraph tool,
MCP 서버, REST 어댑터 어디서든 재사용한다.

    mcrs.py    MCRS 이슈 조회 + resolve_issue (나머지 모듈이 여기에 의존)
    insp.py    INSP MAP / 과거 MAP 이력 / 장비 교차 확인
    review.py  좌표별 REV 이미지 (rev_1~rev_N)
    pm.py      PM 이력 / 공정 trend / PM 전후 비교
"""
