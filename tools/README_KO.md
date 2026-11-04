# 도구 모음 (2026-11-04, 스레드 '적중 확률 높일 도구와 방법 만들기')

## 1. idea_check/ — 연구 아이디어 사전 점검기 (죽은 축 자동 거절)
```
python3 /mnt/project-files/tools/idea_check/idea_check.py check "아이디어 한 줄"
python3 /mnt/project-files/tools/idea_check/idea_check.py list
python3 /mnt/project-files/tools/idea_check/idea_check.py add --id T20 --area 시점 --name "..." --kw "a,b" --verdict CLOSED --result "..." --evidence "경로" --reopen "조건"
```
- 등록부 closed_axes.json: 닫힌 축 50개(시점 19, 종목 14, ETF·배분 5, 레버리지 3, 구조 9). 상태 = 자동 거절 / 막힘(사용자 문) / 전진 기록만 / 진행 중.
- 일치하면 결과 한 줄·근거 파일·다시 열 조건을 보여 주고, 새 축이면 시작 전 점검표(G1, lab, 금지 파일, 2014 이하, 보수 수치)를 찍는다.
- 2015년 이후 수치 없음 → 설계 스레드도 읽어도 된다. 레인이 끝나면 add로 한 줄 넣는다.

## 2. s085_now/ — s0.85 지금 상태 점검기
```
python3 /mnt/project-files/tools/s085_now/s085_now.py --prices qqq.csv   # date,close, 500거래일 이상 권장
```
- C3 신호(200일선 ±2% 관문, 20일 변동성 40%, 금리 역전 378일 경보, 10년 금리 6개월 +1%p 경보)를 연구 코드와 똑같이 계산해 오늘의 목표 레버리지(3배/1배/현금)와 경계까지 여유를 보여 준다.
- 검증: 1984~2014 NDX 7,618거래일에서 연구 코드 bk.C3sig와 목표값 불일치 0.
- 금리: home.treasury.gov 일별 CSV 자동 내려받기(robots 허용). 가격: Twelve Data 또는 Alpha Vantage 연결 도구로 QQQ 일봉을 받아 CSV로 넣는다(원자료는 계산 뒤 지움).
- 계좌 낙폭 브레이크(AV23s)는 계좌마다 달라 계산하지 않는다(새 계좌 = 목표 그대로).
- ⚠ out/ 과 cache/ 에는 2015년 이후 시장 자료가 있다. **연구 설계 스레드는 이 두 폴더를 열지 않는다.**
