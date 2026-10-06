---
name: sk_morning
title: 출근 전 라인 점검
description: 전일 이슈 + 현재 WIP + Open Hold 를 한 번에 정리
tools:
- get_daily_report
- get_wip_status
- get_lot_hold_info
---

1. 전일 이슈 리포트로 P1~P2 항목을 먼저 확인한다.
2. P1 이 장비 DOWN 이면 해당 Area 의 현재 WIP 를 조회해 대기 WIP 를 함께 보고한다.
3. Open Hold 가 있으면 Lot 별 원인을 표로 정리한다.
4. 마지막에 오늘 우선 대응 3가지를 한 줄씩 제안한다.
