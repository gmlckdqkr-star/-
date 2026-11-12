# LH1 추가 1 (계산 전, 2026-11-12 10:0xZ)

등록문 2장 rf 줄의 괄호 안 "TBILL rate_pct"는 사실과 다른 적기 실수다. 같은 줄의 본문 "MS1 경로 그대로"가 기준이며, MS1의 S&P 경로(crash_overlay/mkt.spx, c3_multi/md.load)는 1960년 이전 rf로 TBILL **rate_known_pct**(전월 값)를 쓴다. 점검 C1(real_spx_55_85 = 0.1032181 재현)도 이 값이어야 맞는다. 그래서 rf = rate_known_pct로 계산한다. 1929~1954 성과는 아직 계산하지 않았다. 영향은 조달 금리 한 달 늦음뿐이다(추론: 연 0.01%p 수준).
