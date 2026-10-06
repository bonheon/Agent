---
name: sk_defect
title: Defect 원인 추적
description: Defect Map → Step Overlay → 수율 영향 순으로 원인 추적
tools:
- get_defect_map
- get_defect_step_overlay
- get_defect_yield_history
---

1. Defect Map 으로 유형별 건수와 분포를 확인한다.
2. 가장 많은 유형이 있는 wafer 로 Step 간 Overlay 를 조회해 발생 step 을 찾는다.
3. 해당 유형의 수율 이력으로 kill rate 를 확인하고 결론을 3줄로 정리한다.
