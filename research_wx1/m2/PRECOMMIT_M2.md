# PRECOMMIT M2 — 공개 이상현상 전체(OAP 기업 단위 신호) 종합 점수 + 대량 변형 탐색 (S&P 500 시점 편입)

작성: 2026-11-04 10:41Z, WX1 레인 M2 작업자. 상위 잠금 문서: research/wx1/PRECOMMIT_WX1.md (sha 438d0385…) §1·§3·§5·§7을 그대로 따른다.
이 파일은 **수익 결과를 하나도 계산하기 전에** 잠근다(지금까지 계산한 것: 자료 읽기, 연결, 신호 보유율·순위 분산 — 수익을 읽지 않음, lab 예시 명세 1개의 패리티 실행 stk_mom12_1_top20 — 이미 알려진 예시값).
잠근 뒤 바꾸는 것은 ADDENDUM_M2_n.md로만 하고 이유와 시각을 적는다. 이 파일에는 2015년 이후 수치가 없다.

## 1. 자료
- 종목 우주: lab sp500 v3 패널(research/data/us_stocks/sp500_le2014_v3, 시점별 편입·상폐 포함, lab.stocks.load로 읽어 2014-12-31 뒤 행 버림) ∩ OAP permno 연결(research/influence/results/link_permno_col.csv, 1,319/1,503열). 패널 종목 기호는 결정에 쓰지 않는다(시점 ID·열 번호만).
- 신호: Open Source Asset Pricing(Chen–Zimmermann) Hugging Face OpenSourceAP/CrossSection, 브랜치 Data-Release-2026.10, `Firm Level Characteristics/Predictors.parquet`(209개 신호 열) + SignalDoc.csv(출판 연도 Year, 부호 Sign, 분류 Cat.Economic, Predictability in OP, T-Stat). 읽을 때 yyyymm > 201412 행은 바로 버린다(코드로 assert).
- STreversal(1개월 반전, Jegadeesh 1990)은 파일에 없어 패널 수익(lab 창 규칙: 첫 편입일 뒤 가격만)으로 만든다. Size·Price는 파일에 없고(Price는 lab상 가격 수준 누출 금지 항목이기도 함) 무료 대체가 없어 뺀다.
- 결정일 = lab 월간 결정일(매월 첫 거래일 종가), 체결 = 결정 + 2거래일 종가(lab 지연 2). 보유 수익 = lab `P.R(H_CONS)`(상폐 분류 규칙: 마지막 가격까지 250일 수익 < −30%면 −50%, 아니면 0)로 체결일→다음 체결일.

## 2. 시점 규율
- **출판 규율(McLean–Pontiff)**: 신호 j는 SignalDoc Year(논문 출판 연도) 다음 해 1월 결정부터만 쓴다. 그 전에는 점수에 들어가지 않는다(가중치 추정용 과거 IC는 결정 시점에 이미 실현된 수익만 쓰므로 출판 전 기간 IC도 추정에는 쓴다).
- 부호 = SignalDoc Sign(원 논문 방향). OAP의 공시 지연 규칙은 그대로 둔다.
- **추가 지연 1개월(안전)**: 달력 월 M의 결정은 OAP yyyymm = M−2 행을 읽는다(OAP의 M−1 행은 M 첫날 이미 알 수 있지만 한 달 더 늦춘다). 패널로 만든 STreversal도 M−2월 수익.
- 2014-12-31 뒤 자료는 읽지 않는다.

## 3. 신호 집합 (사전 규칙으로 정함, 수익을 보지 않고 계산)
- 제외 규칙: (a) 출판 2014년 이후(2015년 전 사용 불가), (b) 사용 가능 기간(1986~2014, 출판 다음 해부터)의 결정일 평균으로 자격 편입 종목 중 값 보유율 < 20%, (c) 단면 순위 분산 < 0.01(사실상 상수), (d) 파일에 없음(Size, Price).
- 결과: 212개 중 **사용 168개**(STreversal 포함), 제외 44개. 제외 목록(이유): BetaFP·BetaTailRisk·BrandInvest·CBOperProf·ConvDebt·GrAdExp·OperProfRD·ReturnSkew·ReturnSkew3F·TrendFactor·dCPVolSpread·dVolCall·dVolPut·hire (출판 2014+), AccrualsBM·Activism1·Activism2·AgeIPO·ChNAnalyst·CitationsRD·ConsRecomm·CustomerMomentum·EarnSupBig·FirmAgeMom·IO_ShortInterest·IndRetBig·MomRev·OrderBacklog·OrderBacklogChg·PS·PatentsRD·ProbInformedTrading·RDAbility·RDcap·RIO_Disp·RIO_Volatility·Recomm_ShortInterest·ShareVol·sfe·sinAlgo·std_turn (편입 종목 보유율 < 20%: OAP 정의가 소형주·특정 표본에만 값을 줌), RDIPO (상수), Size·Price (파일에 없음).
- 앞기간(1986~1999)에 한 번이라도 쓸 수 있는 신호(출판 ≤ 1998): 42개. 1986년 1월엔 출판 ≤ 1985인 것만.
- 7개 묶음(Cat.Economic으로 결과 보기 전 지정): VALUE(valuation·leverage·long term reversal, 25개), PROFIT(profitability·profitability alt·composite accounting·earnings growth·payout indicator·cash flow risk·default risk, 21), INVEST(investment·investment alt·investment growth·asset composition·accruals·external financing·sales growth·R&D, 46), MOMENTUM(momentum·lead lag·short-term reversal, 15), RISK(risk·volatility·liquidity·volume·optionrisk·informed trading, 25), ANALYST(earnings forecast·recommendation·earnings event·info proxy, 11), OTHER(other·ownership·short sale constraints, 25).
- 신호 열과 묶음 표: results/coverage.csv.

## 4. 점수(종합)
- 각 결정일, 각 신호: 자격 종목(그날 편입 + 가격 있음) 중 값이 있는 종목의 부호 반영 순위를 (−0.5, 0.5)로 중심화(평균 순위).
- 신호 s를 그 결정에 '쓸 수 있음' = 출판 규율 통과 + 그날 값 있는 자격 종목 ≥ 30.
- 종합 = Σ w_s·r_s / Σ |w_s|·(값 있음) (값 없는 신호는 빼고 정규화). 종목 점수는 Σ|w_s|·(값 있음) ≥ (1/3)·Σ|w_s|·(쓸 수 있음)일 때만 존재(아니면 자격 없음).
- 가중 W (3가지):
  - EQ: 쓸 수 있는 신호에 1.
  - ICW: 과거만 쓴 IC 가중. 신호별 월간 순위 IC(신호 순위 vs 다음 보유 수익) 중 결정 j에 이미 실현된 것(j' ≤ j−2), 최근 120개월(최소 36개월, 모자라면 EQ) 평균 m_s, w_s = max(m_s, 0); 합이 0이면 EQ.
  - RIDGE: 과거만 쓴 능형: w = (C̄ + λI)^(−1) m, m = 위 120개월 평균 IC, C̄ = 같은 창의 월별 신호 순위 단면 상관 행렬 평균(값 없음 = 0), λ = 1. 부호 뒤집힘 허용.
- 상황(C, 6가지) — 사용자의 '상황별 종목 고르기':
  - C0 없음(늘 투자).
  - C1 추세 게이트: 결정일 _SP500EW(lab 시점별 동일가중 편입 종목 지수) ≤ SMA200이면 그 보유 기간 주식 몫 현금(T-bill).
  - C2 거시 게이트: 결정일 lab MS1 거시 경보 inv 또는 csj 또는 shock가 켜져 있으면 현금.
  - C3 국면 전환: 추세 하락 국면(_SP500EW ≤ SMA200)에는 점수를 방어 묶음(PROFIT ∪ RISK, 같은 W)으로 바꾸고 늘 투자.
  - C4 국면별 가중(추세): W를 과거 같은 추세 국면 달만으로 추정(EQ면 '같은 국면 과거 평균 IC > 0인 신호만 1'). 같은 국면 과거 달 < 24면 C0 추정으로 대체. 늘 투자.
  - C5 국면별 가중(거시): C4와 같되 국면 = 거시 경보(inv|csj|shock) 켜짐/꺼짐.
- 업종 중립 SN (2): 끔 / 켬 = 최종 점수를 의사 업종(결정일까지 252거래일 일간 수익으로 k-means k=10, 씨앗 2014, 매년 1월 다시 맞춤; 배정 없는 종목은 별도 묶음) 안 백분위로 바꾼 뒤 전체 상위 K. (무료 SIC가 없어 수익 상관 군집으로 대신함.)
- 급락 거르개 CF (2): 끔 / 켬 = 결정일 21거래일 수익 < −15% 또는 252일 고점 대비 < −40%(lab 창 규칙)인 종목 제외.
- 부분집합 S (17): ALL(168개 전체), 묶음 7개 각각, 묶음 하나씩 뺀 7개, CLEAR(Predictability '1_clear'만), TOPT(OP T-Stat ≥ 사용 신호의 중앙값).
- K ∈ {5, 10, 20, 30, 50}, 동일가중 1/K(자격 종목이 K보다 적으면 남는 몫 현금, lab 규칙).
- 리밸런스 Rb (3): 월간 / 분기(1·4·7·10월 결정) / 3분할(결정 월 mod 3 = 0·1·2인 세 장부, 각 1/3 자본, 3개월 보유, 합산).
- 격자 = S 17 × W 3 × SN 2 × CF 2 × [C0·C1·C2 각각 K 5 × Rb 3 + C3·C4·C5 각각 K 5 × Rb 3] = 17×3×2×2×90 = **18,360개 변형(N)**. 중복 수익 흐름(완전히 같은 월 수익열) 제거 전·후 N을 둘 다 센다.

## 5. 화면 엔진·지표
- 화면 엔진(직접 코드, 이유: lab DSL은 OAP 신호·과거 IC 가중·대량 벡터 탐색을 표현 못 함): 체결일→다음 체결일 보유 수익(위 1), 비용 편도 0.3%(|Δ비중|, 표류 반영, 첫 매수 포함), 세금 없음(세전), 게이트 꺼짐 = T-bill(lab rf_on).
- 지표 x_t = log(1 + r_변형,t) − log(1 + r_EW,t), r_EW = 같은 엔진의 편입 종목 동일가중(월간 리밸런스, 비용 포함). 월 단위.
- 앞기간(선택) = 결정 1986-01 ~ 1999-12(168개월). 뒷기간(1회 확인) = 결정 2000-01 ~ 2014-12(180개월). 뒷기간은 앞기간 상위 20개(x 평균 순, SPA 통과와 무관)만 1회 계산.
- 패리티(탐색 전 필수): (a) 화면 엔진 EW·12-1 모멘텀 상위 20(lab 예시 stk_mom12_1_top20)의 세전 연복리 vs lab 세전(cagr_pretax), (b) 최종 숫자용 lab 엔진 경로(lab.stocks.Targets + fast_run, lab 코드 수정 없음)가 lab run 결과(1986~2014 세후 보수 8.4%, EW 9.9%, MS1 흐름 9.2%)를 재현. 세후 차이 0.5%p 안, 차이는 설명.

## 6. 다중검정 통제 (앞기간)
- SPA: Hansen(2005) 일관 SPA(표준화, 하한 수정 µ̂·1{t > −√(2 ln ln n)}), 정상 부트스트랩 평균 블록 3개월, 1,000회, **전체 N개 변형**, 귀무 = 모든 변형 E[x] ≤ 0(EW 대비).
- Romano–Wolf 단계 하강(같은 부트스트랩, 표준화 최대값) 5% FWER.
- DSR(Bailey–López de Prado): 앞기간 1위(x 평균) 변형의 월간 x 샤프(정보비), 시도 수 N(전체)과 유효 N(변형 x 상관 행렬 고유값의 참여비 (Σλ)²/Σλ², 95% 분산 주성분 수도 함께), 시도 간 샤프 분산 = 전체 변형 샤프의 분산, 왜도·첨도 반영. 기준 ≥ 0.95.

## 7. 확인·MS1·판정 (master §3 그대로)
- 뒷기간 확인: d = 같은 기간 연율 로그 성장(비용 후 세전) 후보 − s0.85(실제 NDX 일간 흐름, MS1 조건 비용 후 세전). (iii) d_뒤 > 0 그리고 d_뒤 ≥ 0.5 × d_앞. EW 대비 x의 앞→뒤 감쇠도 함께 싣는다(정보용).
- 최종 MS1: 뒷기간 통과 변형만, 없으면 앞기간 1위 1개를 '실패 참고'로. 계산 = lab 엔진(Targets + fast_run, H_CONS, 배당세 15.4%, 22% 연 과세, 청산세)으로 세후 1986~2014 + lab ms1_stream과 같은 흐름 → lab ms1.measure_series(같은 코드: std.contexts·ms1eng.series_run)로 다섯 기준. s0.85도 실제 역사 일간 흐름(std.engine, 실제 NDX 1986~2014, 세금 0)을 같은 방식으로 재표본. **대표 환산 = 16.2 + d_stream**, d_stream = dev250_path 경로별 짝 차이(후보 − s0.85 흐름)의 중앙값. 후보 자신의 measure_series 값도 싣는다. 3분할 변형은 lab Targets에서 월간 결정(세 장부 종목을 1/(3K)씩)으로 근사하고 그렇게 표시.
- 통과(P30) = (1) 대표 환산 ≥ 30.0 (2) SPA p < 0.05 + RW 5% 안 + DSR ≥ 0.95 + 확인 (iii) (3) 실제 NDX 1986~2014(흐름 재표본 real_ndx 기준) d ≥ −0.5%p, S&P 1955~85는 신호 자료 없음으로 표시 (4) dd80 ≤ 0.73 × s0.85 흐름 dd80(같은 흐름 재표본 기준). 개선(IMP) = 2~4 + d ≥ +1.0%p. 나머지 실패.
- 정보 우선: ALL·EQ 종합 점수와 묶음별 종합 점수의 앞기간 월간 IC(평균, t), 뒷기간 IC는 앞기간 선택을 잠근 뒤 같이 계산. IS12 기준(1배 30%에 0.08~0.16, 3배 마진 0.05~0.07, 미승인)·WS1 기준(S&P 월간 상위 5 0.101, 상위 20 0.122)과 비교. 실효 IC(IC_eq) = WS1 미국 월간 오라클 곡선(results/map_summary.json US500_h21, K=5·10·20)에서 후보의 lab 세후 1986~2014 값과 같은 값을 내는 IC(근사: 곡선은 1971~2014·WS1 엔진; K 30·50은 K 20 곡선).
- 격자는 IC가 기준보다 훨씬 낮아도 전부 돌린다(사용자가 폭을 원함, 계산이 가벼움).
- 견고성(판정에 안 씀, 앞기간 1위에만): 연결 편향(연결·점수 있는 종목만 EW vs 전체 EW, lab 엔진), 미연결 종목에 무작위 순위를 줬을 때 변화, 상폐 일괄 −30% 행.

## 8. 보고
- RESULT_M2_KO.md: 결론/결과/검증/남은 문제, `lab 사용: 예/아니오(이유)`, N, IC 표 vs 기준, 디플레이션 뒤 숫자를 대표로, 원값은 '원값(선택 편향 포함)'. 통과 0이면 소진 기록(A45). idea_check 등록.
