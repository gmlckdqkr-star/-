# 연구 실험실 (lab) — v2

전략 아이디어를 **짧은 명세 파일(YAML 10~20줄)** 로 쓰면, LLM 없이 로컬에서
개발 구간 요약(≤2014) → 프로젝트 기준 판정 코드(blackbox2 + d6q)로 판정 → 원장 기록까지 하고 **결과를 한 줄**로 돌려줍니다.

## 실행
```
python3 -B -m lab run specs/trend_tqqq_200.yaml specs/qld_088_hold.yaml            # --bar quick (기본)
python3 -B -m lab run specs/x.yaml --bar full [--workers 4] [--all-versions]
python3 -B -m lab run specs/x.yaml --bar none                                       # 개발 요약만
python3 -B -m lab run specs/ --bar quick        # 폴더 = 안의 *.yaml/*.yml/*.json 전부, 끝에 순위 요약표(≤1.5KB)
python3 -B -m lab ledger
python3 -B tests/test_parity.py      # 기존 beat_qld 엔진과 결과 일치 (따로 실행)
python3 -B tests/test_bb.py          # 기준 어댑터 시험 (따로 실행: 두 시험이 서로 다른 engine 모듈을 씀)
python3 -B tests/test_dsl2.py        # v2 문법 시험 (따로 실행)
python3 -B tests/test_stocks.py      # 개별 종목(universe: sp500) 시험 (따로 실행, 약 3분)
```
- 명세가 2개 이상이면 한 줄 결과 뒤에 **요약표**: 빠른 선별 lg 중앙값(10y b63 1000만) 순 상위 10개
  (`이름 hash lg/QLD/QQQM 개발12y 판정·미달관문`; 판정 단계 없으면 개발 12년 배수 순). 전체는 `LAB_HOME/out/batch_<UTC>.json`.
- 개발 요약에도 **인과성 시험**(실제 ≤2014 자료를 무작위 12곳 + 주·월·분기 경계 24곳에서 잘라 비중 비교, plugin은 무작위 300곳)이 붙음.
  위반이면 `개발 인과성 위반`, 개발선별 탈락. 자른 자료는 짧은 것부터, 전체 자료는 마지막에 계산.
- 개발 요약 엔진: `rebalance`가 daily가 아니면 표본일(기간 첫 거래일)마다 목표 비중으로 **되돌려 거래**(고정 비중도 표류하지 않음).
  판정 쪽 중개는 자체 규칙(6% 표류 띠)으로 재조정하므로 두 쪽의 재조정 방식은 다름. daily 명세는 예전과 같음(beat_qld 일치).
- 가격 자료: `LAB_PANEL` (기본 `/mnt/project-files/research/data/panel_f32.npz.xz`)
- 원장·상세 결과: `LAB_HOME` (기본 `lab/var/`, 저장소에 올리지 않음). 상세 JSON은 `LAB_HOME/out/<hash>_<mode>.json`.

## 판정 단계 (`--bar`)
- `quick` — **빠른 선별 (기준 아님)**: 10년 b63 1000만원 1개 실행, 400경로(기준 실행 2000경로의 앞 400경로, 같은 씨앗),
  자체 원천·KRWX·src_end 2014-12-31. Q1·Q2·Q3·R1·R2·R3·W5(7년 배수) 중 미달 이름을 보여줌. 판정 아님.
- `full` — 프로젝트 기준(APPLY-Q60 = A17 Q + A50 G60-W + A49 G-MKT)을 lab이 계산할 수 있는 만큼 적용.
  필요한 4판(자체/공통 × KRWX/DEXKOUS) × Q 실행 10개 + G60-W + G-MKT (a)(b)(c) + 계산 가능한 전제 관문.
  출력 이름:
  - `REJECT` — Q/R 관문 또는 전제(D2, A7, 인과성, 판 불가) 실패 = APPLY-Q 탈락(따라서 APPLY-Q60도 탈락).
  - `REJECT (lab 판정, 미확정)` — Q 수준 실패가 기준 담당 미확인 lab 이식(G4_dev)뿐.
  - `Q60 미달 (Q 미판정)` — G60-W / G-MKT만 실패: APPLY-Q60 미달, APPLY-Q 여부는 lab이 판정 안 함.
  - `PENDING (통합 담당 대기)` — lab이 계산하는 관문은 모두 통과.
  **lab은 APPLY-Q / APPLY-Q60을 출력하지 않음**: PBO, 블라인드 A, DSR(시험 수 N 미정), G7 스트레스(공식 창이 2015+),
  검증 Q, 블라인드 B·D, 파이프라인 관문(recon_crisis_mdd, deep_dd80, deep_mdd_vs_QQQ, deep_underwater_vs_QQQ)은 통합 담당 몫.
  확정 관문이 실패하면 남은 판은 건너뜀(`--all-versions`로 끔). 실제 경로의 lab 이식/해석(G4_dev, G-MKT (c))
  실패로는 멈추지 않음. 판 하나 약 4분(4 작업자) — 동시에 한 개만 실행.
  G-MKT (c) 구간 = 사상 최고점 기준(Generator.bear) ∪ 국지 고점(20% 하락/20% 반등) ∪ 국지 고점→회복 전 최저점의
  합집합(엄격 쪽, lab 해석). 인과성 = 실제 경로(고정 3 + 무작위 40 + 주·월·분기 경계 24 절단) + 부트스트랩 2경로(무작위 40 + 경계 24씩;
plugin은 무작위 300), quick에서도 부트스트랩 2경로.
- `none` — 개발 요약만.
- 판정 가능한 상품: QQQ(→QQQM), QLD, TQQQ, SSO, UPRO, TMF, SPY, TLT, IEF. 그 밖의 상품(SOXL, GLD, SHY …)은
  공통 원천 대용이 없어 `REJECT (version impossible)`.
- 판정 경로의 규칙: 경로마다 명세를 다시 계산(합성 가격), 실제 과거 시세 읽기 차단, 비중은 합 ≤0.88·Σ배율×비중 ≤2.64로 축소,
  워밍업 300일(더 긴 되돌아보기는 처음에 비어 있음), 합성 경로의 month()/weekday()는 의미 없음,
  명세의 `delay`는 판정에 안 씀(중개 지연 0: 종가 결정 → 다음날 시가 체결).
- 명세 검사: `delay`는 정수 ≥2만 허용(그보다 작으면 같은 봉/미래 체결), `cost`는 0.003 미만이면 0.003으로 올림
  (판정 쪽은 비교 기준 QQQM/QLD 보유에도 같은 비용이 들어감).
- **계좌 `account:`** — 기본 `us`(미국 상장 ETF: 편도 0.30%, 연간 순이익 22%). `account: kr_etf` = 국내 상장
  해외지수·레버리지 ETF: 편도 13bp(명세 `cost`로 올리기만 가능), **매도할 때마다 그 이익의 15.4% 원천징수, 손실 상계 없음**
  (보수적. 과표기준가 규칙·ISA 비과세는 반영 안 함), 수익 계열은 같은 상품 계열 그대로(원화 환율·국내 ETF 보수/추적오차 미반영).
  판정 경로는 미국 증권사 기준이라 kr_etf는 개발 요약만 계산하고 기준은 **판정 불가 (KR 계좌)** 로 표시.
  예시 `specs/examples/kr_qld_trend.yaml`.
- **국내 지수 ETF 상품 (kr_etf 계좌 전용)** — `KR200`(069500 KODEX 200), `KRLEV`(122630 KODEX 레버리지),
  `KRINV`(114800 KODEX 인버스), `KRSEMI`(091160 KODEX 반도체). 자기 가격 계열 그대로(상장 전 합성 없음), 패널의
  2007-01~2009-04 공백 때문에 KR200·KRSEMI는 2009-04, KRLEV 2010-02, KRINV 2009-09부터(개발 구간 약 5~6년으로 짧음).
  가격은 미국 거래일 달력에 직전 국내 종가를 이어 붙임(국내 휴장일 수익은 다음 날로 넘어감, 빠짐 없음).
  세금: **국내주식형 ETF 매매차익 비과세로 0** (lab 가정, 세무 확인 전), 다른 상품은 해외지수 ETF로 보고 건별 15.4%.
  `account: kr_etf` 없이 쓰면 오류. 비교 기준은 `baseline: KR200` 권장. 예시 `specs/examples/kr_lev_trend.yaml`.
  229200(코스닥150)은 2014년까지 자료가 없어 뺌. 국내 개별 종목은 아직 없음.
- 코드에 "lab interpretation, bar owner not yet confirmed" 라고 적힌 곳은 기준 담당 확인 전의 lab 해석.

## 미국 개별 종목 (universe: sp500)
S&P 500 편입 종목 안에서 고르는 횡단면 전략. 명세 + `lab run` 한 번, 개발 요약만(판정은 `판정 불가 (개별주)`).
```yaml
name: stk_mom12_1_top20
family: stk_mom
universe: sp500
stock:
  rebalance: month          # month | quarter | week — 기간 첫 거래일 종가에 결정
  score: "ret(252, 21)"     # 종목별 식, 큰 값부터 고름
  filter: "age() >= 252"    # 선택: 종목별 참/거짓 식
  top: 20                   # 또는 top_pct: 0.1
  weight: equal             # equal | invvol(63) | score
  max_weight: 0.10          # 선택: 종목당 상한, 넘는 몫은 CASH
  exposure: up              # 선택: 신호 이름 또는 ETF DSL 식 (참=1, 숫자는 0..1)
  else: {CASH: 1.0}         # 노출 안 된 몫 (CASH 또는 미국 ETF 상품), 기본 CASH
  exposure_every: daily     # daily(기본, 매 종가) | rebalance(결정일만)
signals: {up: "price(_NDX) > sma(_NDX, 200)"}   # 선택, 기존 ETF DSL (ETF 패널, 2014-12-31에서 자름)
```
- **자료**: `research/data/us_stocks/sp500_le2014.npz.xz` (`LAB_STOCKS`로 바꿈). 출처 github.com/Johnbrick123/sp500-data,
  **라이선스 없음 → 개인 연구용, 자료 재배포 금지**(저장소에 올리지 않음). 1968~2014 거래일, 2014년까지 한 번이라도 편입된
  1,503종목, **시점별 편입 구간(PIT)**, **상장폐지·편출 종목 포함**. 수정종가(분할·배당), 거래대금(1996년 전 대부분 없음), 거래 없는 날.
- **종목별 함수** (결정일 행에서만, 창은 결정일 종가에서 끝남): `ret(n[, skip])` skip일 전에 끝나는 n일 총수익,
  `vol(n)` 일간 수익 표준편차, `sma_ratio(n)` 가격/n일 평균, `high_dist(n)` 가격/n일 최고 −1, `dvol(n)` 평균 거래대금(창의 절반
  이상 있을 때), `age()` 첫 가격 뒤 거래일 수, `beta(n)` 동일가중 편입종목 수익 대비 베타, `rank(x)` 0..1 백분위, `csz(x)` z점수
  (rank·csz는 그날 편입·실가격 종목 안에서), `abs min max log`, `+ - * /`, 비교, `and or not`. 창 인자는 숫자 상수만.
  모르는 함수·이름은 오류. 가격 없는 날은 직전 가격(수익 0)으로 잇고, 창 시작일에 가격이 있어야 값이 생김.
- **편입 자격**(결정일 t 종가): t에 편입, t에 실가격(값 있음·거래 없는 날 아님·기록된 거래정지 구간 아님), filter 참, score 값 있음
  (invvol이면 vol도). 보유 종목이 지수에서 빠지면 **다음 결정일에 매도**(미리 팔지 않음).
- **수익·체결**: 수정종가 종가-종가. 거래정지(META `exit_gaps`, 예 EHC −97%)는 가격을 이어 **재개일에 변화 전체**를 씀.
  가격이 끝난 뒤(2014-12-31 전) 다음 날 **−h(상폐 할인)** 한 번, 그 뒤 0. 엔진은 ETF와 같은 `engine.run`(지연 2, 편도 0.30%,
  연간 순실현이익 22%, 마지막 청산 과세, 현금 T-bill)에 개별주용 규칙 하나만 더함: **실가격 없는 날은 그 종목 거래 불가**(정지
  중엔 팔 수 없어 재개일에 다시 시도, 가격 없는 종목은 못 삼). 계산은 같은 규칙의 벡터 빠른 경로(engine.run과 1e-13 일치 시험).
- **한 줄 결과 읽는 법** (모두 ≤2014, 세후 = 22% 과세 뒤 CAGR):
  `개별주 S&P500(시점편입·상폐포함) 1986~2014 세후 보수 x% (기본 y%·극단 z%) 낙폭 m% 평균 n종목 회전 t x | 동일가중 a% · NDX보유 b% |
  1971~2014 c% | 무작위 바구니 상위 p% (95%선·99%선 통과/미달) | Sharpe s (G1 1.1 통과/미달) | 기준: 판정 불가 (개별주)`
  - **보수 x% = 대표값**: 보유 중 가격이 끝나면 모두 −30%(h=0.30). 기본 y% = h=0(마지막 가격에 청산). 극단 z% = 기본 + 보유 종목마다
    해마다 6% 확률 −100% (씨앗 고정 20회 중앙값, 참고용). 낙폭·평균 종목 수(노출 안 된 날 0)·회전(연간 매수+매도/평가액)은 보수 행.
  - 동일가중 a% = 매월 편입 종목 전부 동일가중(같은 엔진·비용·세금·h=0.30). NDX보유 b% = lab QQQ 상품 1배 보유(1999년 전 _NDX 가격지수,
    배당 없음). 1971~2014 c% = 보수 행의 긴 구간(`else`가 ETF면 그 상품 자료 시작부터; 게이트 자료가 늦게 시작하면 `(게이트 1985~)`).
  - 무작위 바구니: 같은 결정일·같은 자격(filter·score 값)·같은 종목 수, 동일가중, 같은 노출·엔진·비용·세금·h=0.30으로 200개(씨앗 고정).
    **설계와 다른 점**: 매번 새로 뽑으면 이름 회전이 ~95%라 비용·세금을 전략보다 훨씬 많이 내서 어떤 전략이든 좋아 보임 →
    직전 바구니에서 **전략이 남긴 종목 수만큼**(아직 자격 있는 것 중 무작위) 남기고 나머지만 새로 뽑아 회전을 맞춤.
    `상위 p%` = 1986~2014 세후 보수 CAGR이 무작위 바구니 중 위에서 p% 자리, 95%선·99%선 = 그 백분위를 넘었는지.
  - Sharpe = 1986~2014 보수 행의 **비용 뒤·세금 전** 일간 수익에서 T-bill을 뺀 연율 Sharpe. G1 비타이밍 관문 1.1 이상이면 통과.
  - 상세(모든 행, 1971 구간, 무작위 200개 CAGR, 극단 20개, 마지막 결정일 종목)는 `LAB_HOME/out/<hash>_<bar>.json`. 2014년 뒤 상폐
    날짜가 붙은 종목 이름(예 AET-201811)은 `AET*`로 가림. 해시·계열 N에 `universe`·`stock` 포함, `grid:`로 stock 값도 훑을 수 있음.
- **한계**: S&P 500 편입 종목만(소형주·편입 전 종목 없음), 재무자료 없음(가격·거래대금만), 1996~2000 crsp-patch 행 약 0.9%는
  다른 출처와 1%p 넘게 다름(어느 쪽이 맞는지 미확정), 수정가격만 있어 **실제 거래가격 수준 필터(저가주) 불가**, `dvol`은 1996년 전
  대부분 없어 dvol 조건을 쓰면 그 전엔 종목이 없어 현금. h=0.30은 인수(현금·주식 지급)도 손실로 보므로 하한에 가까움 — 인수 대상이
  되는 종목을 많이 사는 전략(호가 뒤 오른 종목을 사는 모멘텀 등)이 특히 깎임. 전액 손실 종목은 팔 값이 없어 세금 상계가 마지막
  청산으로 밀림(엔진 규칙), 거래정지 중인 종목도 다른 종목 거래 비용을 비례로 나눠 냄. 한 명세 약 10~25초(첫 패널 읽기 약 6초 별도).
- 예시 `specs/examples/stk_*.yaml`: `stk_mom12_1_top20`(12-1 모멘텀 상위 20), `stk_lowvol_top50`(저변동 50, 역변동성 비중, 분기),
  `stk_mom_trend_gate`(모멘텀 20 + _NDX > SMA200일 때만, 아니면 현금), `stk_quality_proxy`(가격만으로 만든 품질 대용: 추세·저변동·
  고점 근접 순위 합, 상위 30).

## 봉인 (코드로 강제)
- 모든 시뮬레이션은 src_end='2014-12-31'을 명시해서 실행. 경로 생성기를 감싸서 그 뒤 날짜로는 생성 자체가 안 됨.
- 2015년 이후 구간은 계산·출력·저장하지 않음. 예전 MVP의 봉인 구간 PASS/REJECT 판정과 계열별 횟수 예산은 삭제.
- 개발 요약(≤2014 실제 자료 + 짝 재표본)은 **개발 선별 (기준 아님)** 표시만 함.
- 개별주 패널은 2014-12-31 뒤 행을 읽는 즉시 버림(`stocks.Panel`), 게이트 신호·T-bill·ETF 상품 계열도 잘라서 씀, 결과 색인은
  `_sealed`로 확인(넘으면 SealError).
- 같은 명세(해시 같음)는 다시 계산하지 않음. 계열별 시험 수 N을 셈. 기준 결과는 (해시, 단계)별로 저장.

## DSL 요약표 (v2)
식은 문자열, 이름은 상품명(`QLD`)이면 그 **기초지수**(QLD→나스닥100), 따옴표/패널 이름(`'KRW_X'`, `_IRX`)은 그 시계열.
창·지연·기간 인자는 정수 ≥1만(0·음수 = 미래 행 → 오류). `and or not`, 비교 연쇄, `+ - * / % **`, 이름 목록 `[QLD, TLT]`만 허용.

| 함수 | 뜻 |
|---|---|
| `price(x)` `sma(x,n)` `ema(x,n)` `ret(x,n)` `vol(x,n)` `high(x,n)` `low(x,n)` `dd(x,n)` `rsi(x,n=14)` | 기본 지표 (vol = 연율 로그수익 표준편차) |
| `month()` `weekday()` `min(a,b)` `max(a,b)` `abs(a)` `lag(s,n=1)` | 달력·산술·지연 (합성 경로에서 달력은 의미 없음) |
| `latch(on, off)` | on이면 켜짐, off면 꺼짐, 아니면 유지. 처음 꺼짐, 같은 날 둘 다면 off |
| `corr(x, y, n)` | n일 상관 (이름 = 일간 로그수익, 식 = 그대로) |
| `zscore(s, n)` | (s − n일 평균)/n일 표준편차 (이름 = 가격) |
| `ewvol(x, halflife)` | 지수가중 연율 변동성 (halflife > 0) |
| `since(cond)` | cond가 마지막으로 참이던 날부터 지난 날수 (참인 날 0, 한 번도 없으면 inf) |
| `hold_min(cond, n)` | cond가 켜진 날부터 최소 n일 켜둠, 그 뒤엔 cond 따라감 |
| `invvol(x, [a,b,..], n)` | 목록 안 역변동성 비중 중 x의 몫 (변동성 = 배율 × 기초지수, 합 1) |
| `rp(x, [a,b,..], n)` | 위험균형(위험기여 같게) 비중 중 x의 몫 (n일 공분산, 음의 상관도 정확히 풂: 두 상품이면 invvol과 같음) |
| `level(x)` | 보유 상품 x의 **거래 가격 수준**(개발 = 상장 전 합성 포함 누적 수익, 판정 = 경로의 x 가격). 비율로만 쓸 것, 예 `level(TQQQ) / high(level(TQQQ), 252)` |

invvol·rp는 목록의 **모든** 상품에 n일 변동성이 생긴 날부터 값이 있음(그 전엔 0). 지표 함수(`sma` `high` `dd` `vol` …)의 첫 인자는
이름 또는 식(예 `sma(level(TQQQ), 50)`). 상수 계산은 실수로 해서 `10**10**9` 같은 식은 바로 오류. 신호 이름은 식별자만:
YAML은 `on` `off` `yes` `no`를 참/거짓으로 읽으므로 신호 이름으로 못 씀(`latch(go, stop)`처럼).

**규칙** (`rules`, 위에서부터 처음 맞는 것): `- when: 식` + `hold: {상품: 비중식}` / `- else: {..}`(else 줄엔 다른 키 없음) /
`- [when: 식] rotate: {..}`. 비중 합 >1이면 1로 줄이고 나머지는 CASH.

**rotate** — `assets: [..]`(필수), `score: 식`(`*` = 각 상품, 예 `ret(*, 126)`), `filter: 식`(`*` 사용),
`top: k`(score 있으면 기본 1, 없으면 전부), `weight: equal|score|invvol|rp`(기본 equal; score = 양수 점수 비례),
`n: 60`(invvol·rp 기간), `every: daily|weekly|monthly|quarterly|N`(기본 monthly, 기간 **첫 거래일**에 결정),
`exit: daily`(결정일 사이 filter 깨지면 그날부터 다음 결정일까지 뺌), `total: 0.88`(합, 기본 1),
`fill: 상품`(빈 자리 몫, 기본 CASH). 고른 수 m < k이면 총합 × m/k만 담고 나머지는 fill.

**전체 후처리 순서**: 규칙(또는 plugin) → 합 ≤1 → `rebalance`(daily|weekly|monthly|quarterly|N, 기간 첫 거래일 표본)
→ `brake` → `band`.

**brake** (자기 장부 낙폭 제동) — 장부 = 전략 자신의 비중(전날 결정) × 상품 종가-종가 수익, **비용·세금 없음, 현금 수익 0**,
첫 행부터(판정 경로는 워밍업 300일 포함; G0 상한 축소 전 비중). t일 비중은 t일 종가까지의 장부만 씀(인과).
- `{dd: -0.20, scale: 0.5, recover: -0.10}` 낙폭 ≤-20%면 0.5배, -10% 이상 회복하면 복귀 (recover 기본 dd/2)
- `{ladder: [[-0.10, 0.75], [-0.20, 0.4], [-0.30, 0.0, -0.12]], recover: -0.05}` 단계별(각 단계 [dd, 배수(, 복귀)]), 가장 작은 배수
- `{knee: [-0.45, -0.75], floor: 0.0}` -45%부터 -75%까지 선형으로 1→floor (복귀 지연 없음)
- 공통: `basis: own|raw`(own = 제동된 자기 장부, 기본; raw = 제동 전 장부), `cooldown: N`(N일 넘게 제동이면 풀고 고점 재설정
  — own + scale 0은 장부가 멈춰 영영 안 풀리므로 이걸 쓰거나 raw), `floor_when: {when: 식, scale: s}`(그날 최소 배수).
- 경로당 계산 ~1–2ms(10년+워밍업 2821행), 경로당 전체 비중 계산 ~2–3ms.

**grid** — `grid: {X: [0.25, 0.30, 0.35]}` + 명세 어디든 `{X}`. 점마다 별도 명세(이름 `base[X=0.25]`, 해시 따로,
원장에 따로, **계열 N에 각각 셈**). 값 전체가 `'{X}'`면 숫자 그대로. 키 여러 개면 곱집합(최대 256점).
`name` `family` `known` `baseline`에는 `{X}`를 못 씀(점마다 계열이 갈리면 N을 못 셈).

**plugin** (DSL로 **못 쓰는 모양**에만) — `plugin: plugins/f.py:func`(명세 파일 기준 경로), `sleeves: [..]`(필수),
`inputs: [QQQ, 'level(TQQQ)', 'vol(QQQ, 20)']`(F의 열: 이름 = price()와 같은 뜻, 그 밖은 DSL 식; 열 이름 = 그 문자열),
`params: {..}`. `func(F, sleeves, params)` → F와 같은 index, 열 ⊂ sleeves+CASH인 비중 DataFrame. 개발 요약과 판정 경로마다 실행,
후처리(rebalance·brake·band) 동일. 해시 = 파일 내용.
- **격리**(`lab/sandbox.py`): plugin 코드는 lab·판정 프로세스에서 **실행되지 않음**. 작업 프로세스마다 numpy·pandas만 올린 별도
  인터프리터를 띄우고, 호출(세션)마다 거기서 새 자식 프로세스를 fork. 자식은 받은 F만 가짐(패널·lab·blackbox 없음), 파일·소켓을
  새로 못 엶(RLIMIT_NOFILE), root면 nobody로 내려감(lab에 신호 못 보냄), fork 불가, CPU 제한, 프레임당 120초 시간 제한
  (`LAB_PLUGIN_TIMEOUT`). 모듈 상태는 호출 사이에 안 남음. 결과는 JSON + 숫자 버퍼로만 받음(pickle 안 씀).
  `SystemExit` 등 무엇을 던져도 그 명세의 `PluginError` 한 줄이고 배치는 계속.
- 소스 검사(빠른 오류용): import는 numpy pandas math itertools functools collections statistics bisect heapq operator re만,
  `__x__` 이름 금지, open / np.load / os / sys / /mnt … 금지.
- 인과성: 세션 안에서는 **앞 프레임을 늘인 프레임**만 같은 자식에 보냄(가진 상태 = 이미 받은 행뿐). 절단 시험은 짧은 것부터,
  전체를 마지막에 보내므로 저장해 둔 전체 답을 잘린 호출에 되돌려 주는 수법이 안 통함. plugin은 경로당 무작위 300곳 + 경계 절단.
- 비용: 판정 경로 1개 계산마다 fork 1번(~10ms). quick은 몇 초 늘고, full(판당 경로 수만 개)은 4 작업자 기준 판당 수 분 늘 수 있음.

**판정 경로가 재표본하지 않는 입력**(`_IRX` 등 거시, `*.KS`, `KRW_X`, GLD·SHY 같은 대용 없는 상품)은 식·rotate·목록·
floor_when·plugin inputs 어디에 있든 개발 요약은 계산, 판정은 `REJECT (version impossible)`(NotJudgeable). (`_TNX`는 패널에 없음.)

### 예시 1 — rotation (`specs/rotate_dualmom.yaml`)
```yaml
name: rotate_dualmom
family: rotation
rules:
  - rotate: {assets: [QLD, SSO, TLT], score: 'ret(*, 126)', filter: 'price(*) > sma(*, 200)',
             top: 1, every: monthly, exit: daily, total: 0.88}
```
### 예시 2 — brake (`specs/brake_qld.yaml`)
```yaml
name: brake_qld
family: dd_brake
rules:
  - else: {QLD: 0.88}
brake: {dd: -0.25, scale: 0.5, recover: -0.10}
```
### 예시 3 — grid (`specs/grid_trend_qld.yaml`, 시험 3개)
```yaml
name: grid_trend_qld
family: price_trend
grid: {N: [150, 200, 250]}
signals: {up: 'price(QQQ) > sma(QQQ, {N})'}
rules:
  - when: up
    hold: {QLD: 0.88}
  - else: {CASH: 1.0}
```
plugin 예시: `specs/plugin_reentry.yaml` + `specs/plugins/reentry_wait.py`.

### 예시 모음 (`specs/examples/`, `lab run specs/examples/`로 한 번에)
- `bq_*` — research/beat_qld 전략을 lab으로 다시 쓴 것(계열 `beat_qld_repro`). B·G·K·M은 DSL, C·D는 rotate, I는 monthly 규칙:
  개발 비중이 원본과 일치(C·D·I는 원본의 **월말** 결정을 **월초**로 옮긴 판과 일치 — 월말 결정은 다음 날짜를 알아야 해서 인과성
  위반). H·J는 plugin(월 표본 10개월 평균, 월초 결정), E는 plugin + `inputs: ['level(TQQQ)']`로 strats.E와 개발 비중 일치.
  계좌 여러 개를 섞는 combo는 lab으로 못 씀.
- `f10_monthly_trend_mom`, `f13_static_mix_quarterly`(고정 혼합, 분기 재조정), `ivol_tqqq_tmf`·`ivol_tqqq_tmf_rotate`(같은 비중을
  식과 rotate 두 가지로), `rp_tqqq_tmf`(두 상품 위험균형 = 역변동성) — 상수는 탐색 안 한 교과서 값.

판정 BAR_VERSION 3 / 개발 요약 DEV_VERSION 2: rp 풀이, invvol 시작, plugin 격리, 절단 위치, 개발 엔진 재조정이 바뀌어서
예전에 저장된 판정·개발 결과는 다시 계산함(해시·계열 N은 그대로).

v1과 달라진 점: weekly/monthly `rebalance`가 기간 **마지막** 거래일 → **첫** 거래일 표본으로 바뀜(옛 방식은 다음 날짜를
알아야 해서 판정 인과성 시험에 걸림). 그래서 weekly/monthly 명세는 해시가 새로 생김(daily 명세 해시는 그대로).
