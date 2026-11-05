# PRECOMMIT DV2 — 살 수 있는 2배·3배 ETF를 s0.85 옆에 고정 비중으로 (2026-11-05, 숫자 계산 전 등록)

자료 <= 2014-12-31. 금지 파일 열지 않음. 유료 자료 없음. 엔진 = DV1과 같은 el._comb (MS1: 0.3%/편도, 22% 연 실현, 250만 공제, 청산세, 21일 띠 재조정 5%/25%).
DV1 결과(사전 1순위 TQQQ 10% = DV-FAIL; 가치+수익성 레버리지 표)는 본 뒤에 쓴다. 이 등록의 흐름(업종·소형주)은 아직 한 번도 결합으로 재지 않았다.

## 1. 후보 (N = 76)
업종 원자료 = 프로젝트 calendar의 Ken French 업종 9개(TECH FIN ENER HLTH UTIL STAP MANU SHOP TELE), 소형주 = KF 6 Portfolios 2x3 SMALL 3칸 평균(가치가중), S&P500 = SPX.
합성 = sl.asset('eq', r, L): L*r − (L−1)rf − 2.45%/년 (MS1 3배 비용을 2배에도 그대로, 보수적).
- 2배(현존 ProShares Ultra 계열 대응): HLTH(RXL) UTIL(UPW) FIN(UYG) ENER(DIG) SHOP(UCC) MANU(UXI) STAP(UGE) TELE(LTL) SMALL(UWM) SPX(SSO) TECH(ROM) = 11
- 3배(현존 Direxion 등 대응): HLTH(CURE) UTIL(UTSL) FIN(FAS) SHOP(WANT) MANU(DUSL) SMALL(TNA) SPX(UPRO) TECH(TECL) = 8
  → 흐름 19개 × 비중 w ∈ {0.1,0.2,0.3,0.4} = 76 (N = 76)
- 늘 보유, 1년 세금 통 하나, 띠 재조정.

## 2. 고르기 (앞 시대만: 1955~85)
- 점수 = min( d(real_spx_55_85), d(real_spx_70_85) ), d = 같은 경로 결합 연복리 − s0.85 연복리(%p, MS1 전체 기간 값).
- 1순위 = 점수 최고(동점이면 w 작은 쪽). 5순위까지 확인 표에 싣는다(판정은 1순위로만).

## 3. 확인 (1986~2014, 고르기에 안 씀)
1순위가 모두 넘으면 'DV2-OK', 아니면 'DV2-FAIL'.
- (a) dev250_path 짝 차이 중앙 >= 0, 이긴 경로 >= 55%
- (b) 실제 NDX 86~14 d >= −1.0%p (s0.85 최고 시대라 작은 희석만 허용)
- (c) 실제 NDX 2000~14 조각 d >= 0
- (d) dev250_path 낙폭 중앙 >= −90% (사용자 11-05 00:54Z 허용선) 이고 −80% 확률이 s0.85보다 높지 않음
- (e) 비용 2배 path 짝 차이 중앙 >= −0.3%p
- 보고: 대표값 = dev250_path 결합 연복리 중앙, 5개 기준 표, N 76 선택 보정 표시(개발 구간 측정).
