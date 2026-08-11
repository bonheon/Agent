"""MCRS 분석 skill 의 비즈니스 로직.

순수 파이썬 — LangChain/LangGraph 의존이 없다. 같은 함수를 LangGraph tool,
MCP 서버, REST 어댑터 어디서든 재사용한다.

    context.py 공정 이력 → 장비·device·처리시각 (범용 조회의 기반)
    mcrs.py    MCRS 이슈 보강 + resolve() (조회 tool 의 단일 진입점)
    insp.py    INSP MAP / 과거 MAP 이력 / 장비 교차 확인
    review.py  좌표별 REV 이미지 (rev_1~rev_N)
    pm.py      PM 이력 / 공정 trend / PM 전후 비교

의존 방향은 context ← mcrs ← {insp, review, pm} 한 방향이다. 장비·device 를
공정 이력(context)에서 얻고 MCRS 는 그 위에 얹기 때문에, MCRS 가 없는 Lot 도
조회가 막히지 않는다.
"""
