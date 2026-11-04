---
name: s085-monthly-check
description: Report what the s0.85 trading method says right now (3x / 1x / cash target, macro warnings, distance to the switch points) for the 자동 매매 프로그램 project; use when the user asks for the current s0.85 position, signal, or a monthly check.
---

# s0.85 지금 상태 점검

## 순서
1. QQQ 일봉 종가를 최소 500거래일 받는다. Twelve Data 연결 도구 `get_time_series`(symbol QQQ, interval 1day, outputsize 520)를 먼저 쓰고, 안 되면 Alpha Vantage `TIME_SERIES_DAILY`(outputsize full). Financial Datasets는 절대 쓰지 않는다.
2. 날짜와 종가만 `date,close` CSV로 scratchpad에 쓴다(오래된 날짜가 위).
3. 실행:
   ```
   python3 /mnt/project-files/tools/s085_now/s085_now.py --prices <scratchpad>/qqq.csv
   ```
   금리(10년, 3개월)는 스크립트가 home.treasury.gov에서 직접 받는다. 패키지가 없으면 `pip install pandas numpy`.
4. 보고서 끝의 '추세 관문 상태'가 미확정이면 가격을 더 길게 받아 다시 돌린다.
5. 계산이 끝나면 scratchpad의 가격 CSV를 지운다(자료 제공자 보관 조건).

## 보고 (한국어, 짧게)
- 결론: 오늘 목표 레버리지(3배 / 1배 / 현금)와 이유 한 줄.
- 결과: 200일선 대비 위치, 20일 변동성, 금리 역전 경보·급등 경보 상태, 전환까지 남은 여유.
- 검증: 가격 마지막 날짜, 관문 상태 확정 여부.
- 남은 문제: 계좌 낙폭 브레이크(AV23s)는 계좌마다 달라 반영 안 됨(새 계좌 = 목표 그대로). 실제 주문은 프로그램 기준.
- 성과 숫자(수익률)는 새로 만들지 않는다. 필요하면 'MS1 대표값 16.2%(2014년 이하 개발 구간)'만 인용한다.

## 주의
- tools/s085_now/out/ 과 cache/ 에는 2015년 이후 자료가 있다. 연구 설계 스레드에는 이 경로를 주지 않는다.
- 주문을 넣거나 프로그램 설정을 바꾸지 않는다. 상태 보고만 한다.
