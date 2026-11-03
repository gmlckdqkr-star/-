# 연구 실험실 (lab) — v2

전략 아이디어를 **짧은 명세 파일(YAML 10~20줄)** 로 쓰면, LLM 없이 로컬에서
개발 구간 요약(≤2014) → 프로젝트 기준 판정 코드(blackbox2 + d6q)로 판정 → 원장 기록까지 하고 **결과를 한 줄**로 돌려줍니다.

## 실행
```
python3 -B -m lab run specs/trend_tqqq_200.yaml specs/qld_088_hold.yaml            # --bar quick (기본)
python3 -B -m lab run specs/x.yaml --bar full [--workers 4] [--all-versions]
python3 -B -m lab run specs/x.yaml --bar none                                       # 개발 요약만 (+ MS1·G1)
python3 -B -m lab run specs/ --bar quick        # 폴더 = 안의 *.yaml/*.yml/*.json 전부, 끝에 순위 요약표(≤1.5KB)
python3 -B -m lab run specs/x.yaml --std none   # MS1·G1 생략 (기본 --std auto, --std ms1 | g1 | ms1,g1)
python3 -B -m lab setup                          # MS1 계산 환경 (한 번, 아래 'MS1·G1 자동 보고')
python3 -B -m lab ledger
python3 -B tests/test_parity.py      # 기존 beat_qld 엔진과 결과 일치 (따로 실행)
python3 -B tests/test_bb.py          # 기준 어댑터 시험 (따로 실행: 두 시험이 서로 다른 engine 모듈을 씀)
python3 -B tests/test_dsl2.py        # v2 문법 시험 (따로 실행)
python3 -B tests/test_ms1.py         # MS1·G1 시험 (따로 실행, MS1 환경 필요)
```
- 명세가 2개 이상이면 한 줄 결과 뒤에 **요약표**: 빠른 선별 lg 중앙값(10y b63 1000만) 순 상위 10개
  (`이름 hash lg/QLD/QQQM 개발12y MS1경로·G1 판정·미달관문`; 판정 단계 없으면 개발 12년 배수 순).
- 한 줄이 400바이트를 넘으면 개발·판정·MS1 부분을 같은 숫자의 짧은 꼴로 바꿈(그래도 넘으면 끝을 자름). 전체는 `LAB_HOME/out/batch_<UTC>.json`.
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

## 봉인 (코드로 강제)
- 모든 시뮬레이션은 src_end='2014-12-31'을 명시해서 실행. 경로 생성기를 감싸서 그 뒤 날짜로는 생성 자체가 안 됨.
- 2015년 이후 구간은 계산·출력·저장하지 않음. 예전 MVP의 봉인 구간 PASS/REJECT 판정과 계열별 횟수 예산은 삭제.
- 개발 요약(≤2014 실제 자료 + 짝 재표본)은 **개발 선별 (기준 아님)** 표시만 함.
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
| `macro(k)` | MS1 거시 경보 8개 중 하나(참/거짓): `inv` `inv2`(장단기 역전 378/504일 안) `shock` `shock10`(10년물 1년 +1.5/+1.0%p) `shock6m` `shock6m75` `shock3m`(6개월 +1.0/+0.75, 3개월 +0.75%p) `csj`(신용 스프레드 급등). 개발 = 실제 경보(`lab/macro_flags_le2014.csv.gz`, ≤2014, `tools/build_macro_flags.py`), MS1 경로 = 그 기준의 경보, 판정 경로엔 없음 → `REJECT (version impossible)`. `macro(inv)` = `macro('inv')` |

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

**판정 경로가 재표본하지 않는 입력**(`_IRX` 등 거시, `macro(k)`, `*.KS`, `KRW_X`, GLD·SHY 같은 대용 없는 상품)은 식·rotate·목록·
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
- `macro_trend_tqqq` — `macro(k)` 예시(200일 평균 아래 + 역전/금리 급등 경보면 현금, 아니면 TQQQ).

## MS1·G1 자동 보고 (`--std auto`, 기본)
프로젝트 고정 측정 기준 **MS1**(`research/measure_std/MEASURE_STD_KO.md`, `std.py`)과 정보량 관문 **G1**
(`research/breakthrough/INFO_GATE_KO.md`, `code/gate.py`)을 lab이 자동으로 재서 한 줄에 붙임. 모두 개발 구간(≤2014) 숫자.
```
MS1 경로 5.7% (하한 5.7%, s0.85 16.2·1x 11.6) dd80 98% s0.85대비 -10.3%p 승 6% §5엔진 | G1 NDX 52.9(상시55.5) SPX 53.0(55.7) 보정 47.5 N=1 닫음 CLOSE
```
- **MS1**: 경로 = dev250_path 30년 세후(청산세 포함) 연복리 중앙값(MS1 대표값). 하한 = std.measure의 `FLOOR_MS1`
  = min(dev250_path, 실제 NDX 86~14). 괄호 안 = 같은 기준의 s0.85·1배 보유. dd80 = 경로 중 MDD ≤ −80% 비율.
  s0.85대비 = 같은 경로끼리 짝지은 차이의 중앙값(%p), 승 = s0.85를 이긴 경로 비율. 다섯 기준 전체(glued, 실제 NDX,
  S&P 55~85·70~85, 1·2·3배 보유, 연 거래 수)는 `LAB_HOME/out/<hash>_<bar>.json`의 `std`.
- **G1**: 실제 나스닥100 1986~2014 / S&P500 1955~1985 21일 블록 적중률(괄호 = 늘 들고 있기 적중), 보정 = 낮은 시대의
  적중 − 2·SE·√(1+ln N)(N = 원장의 계열 시도 수), 판정 `닫음 CLOSE` / `보류 HOLD` / `설계 BUILD` / `60%후보 60%-CANDIDATE`.
  시장 안 = 종가 t의 위험 비중 합 > 0. 명세를 실제 전체 틀(NDX 1984~2014, SPX 1928~1985: SPX 수준을 `_NDX` 자리에, 상품은
  SPX 수익으로)에서 계산하고 1986-01-01 전은 SPX 신호, 뒤는 NDX 신호. 한 시대라도 늘 안(또는 늘 밖)이면
  `G1 해당 없음 (상시 보유)` + 비용 후·세전 연 샤프(실제 NDX 86~14·S&P 55~85 중 낮은 쪽) vs 1.1 — INFO_GATE의 MS1 기준 샤프
  (0.55 등)와 정의가 달라 섞지 않음.
- **자격**: `account: us`, 보유 ⊂ {QQQ, QLD, TQQQ, CASH}, 읽는 계열 ⊂ {QQQ, QLD, TQQQ, _NDX} + `macro(k)`. 그 밖은
  `MS1: 해당 없음 (이유)`(예 `보유 SSO,TLT: QQQ·QLD·TQQQ·CASH만`). plugin 명세도 됨(경로마다 격리 실행이라 느림).
- **엔진 = MS1-조건 sleeve 엔진** (`lab/ms1eng.py`, 줄 끝 `§5엔진`): std.measure의 엔진은 수준 L을 TQQQ L/3 + 현금으로 들어서
  QQQ·QLD 명세엔 틀린 값을 냄(B=1 → 2.9%, 1배 보유 11.6%가 아님). 그래서 명세의 QQQ·QLD·TQQQ·현금 비중을 그대로 거래하는
  엔진을 따로 두고 beng(= std.engine)의 1장 조건을 그대로 씀: 편도 0.3%, 해마다(252일) 실현 순이익 − 250만(시작 1천만 → 0.25)의
  22%를 비례 매도로 납부, 이월결손 없음, 해 끝에 공제만큼 이익(또는 초과 실현이면 손실) 실현(beng harvest), 마지막 날 청산세,
  2·3배 = L·r − (L−1)·rf − 2.45%/년, 1배 0.2%/년, 현금 (rf − 2%p)·(1 − 15.4%), 체결 지연 2, 나스닥100 가격지수, 다섯 기준
  (std.contexts() 그대로). MEASURE_STD_KO.md 5장이 허용하는 '1장 조건·2장 기준이 같은 별도 엔진'.
  명세는 경로마다 lab DSL 그대로 계산: `_NDX` = 경로 지수, 보유 상품 수준 = MS1 비용 수익(level(x)·brake), `macro(k)` =
  그 기준의 경보(dev250_path = 경로 위 재계산, glued = 원래 날짜, 실제 기준 = 실제), month()/weekday() = 경로 행의 원래 날짜.
  명세의 cost·delay는 안 씀(MS1 0.3%·지연 2), `rebalance:` 표본일엔 목표로 되돌려 거래, 수준 반올림 없음(비중이 바뀌면 거래).
- **일치 시험** (`tests/test_ms1.py`):
  - TQQQ 상수 = MS1 3배 보유 행, 다섯 기준 모두 정확히(4.23 / 4.23 / 3.87 / 9.84 / 4.35).
  - TQQQ+현금 명세 = 같은 명세의 std.measure와 정확히 일치: trend_tqqq_200(경로 5.73, 실제 NDX 6.08, S&P55 11.56),
    macro 경보 명세(경로 10.77, glued 22.57), TQQQ 0.5. **연속 비중**(변동성 비례 TQQQ)은 경로 11.15 vs 13.46: beng은 수준을
    0.1/0.5 단위로 반올림하고 한 단위 넘게 움직일 때만 거래, sleeve 엔진은 비중이 바뀔 때마다 0.3%로 거래(연 250회) —
    순서 단위 규칙 차이. 연속 비중 명세는 `band:`로 거래를 줄일 것.
  - QQQ·QLD 상수 vs std.hold 1·2배 행: 세전 곡선은 정확히 비례(수익 공식 일치). 세후 차이(경로 / glued / 실제 NDX / S&P55 / S&P70):
    1배 +0.07 / +0.07 / +0.13 / +0.01 / +0.58%p, 2배 +0.12 / +0.12 / +0.24 / +0.06 / +0.43%p. 이유: std.hold의 1·2배는 공제 없이
    마지막에 한 번 과세하는 별도 식이고, sleeve 엔진은 s0.85·3배 행과 같은 beng 규칙(해마다 250만 공제만큼 이익 실현)을 씀.
    그래서 이 두 행은 0.05%p 안으로 안 맞음(숨기지 않음). 공제 효과는 수익이 낮은 시대(S&P 70~85)에서 큼.
  - `measure_series`에 나스닥100 1배 흐름(0.2%/년, 회전 0) → 1배 보유 행과 경로 −0.007, 실제 NDX −0.006%p.
  - G1 자체 점검: 늘 안 55.46 / 55.68 닫음, 미래 오라클 1.0, SMA200(trend_tqqq_200) 52.87 / 52.97 닫음.
- **`ms1.measure_series(dates, daily_ret_after_cost, label, turnover=1.0)`** (다른 명세 종류용 API): 임의의 일간 수익 흐름을
  같은 경로 색인 행렬로 다시 표본(IS1 방법, research/indiv_stock/code/bases.py + eng.py), s0.85와 경로별 짝. 세금 = 252일마다
  22% × max(min(1, 회전) × 미실현 이익 − 0.25, 0), 이월 없음, 진입·청산 비용 0.3%, 청산세. 흐름이 덮지 못하는 기준(사용 날의
  95% 미만, 예 1986년 이후 흐름의 S&P 시대)은 None. 2014-12-31 뒤 행은 버림. 표시 `MS1 (수익 흐름 재표본, 경로 재계산 없음)`.
- **준비**: `python3 -B -m lab setup` → `LAB_CACHE/ms1-venv`(기본 `~/.cache/lab/ms1-venv`, PyPI에서 numba scipy xlrd numpy
  pandas pyyaml, 1~2분, 약 500MB). 없으면 `lab run`이 한 번 알아서 설치(`MS1 계산 환경 설치 중 ...` 한 줄), 실패하면
  `MS1: 설치 실패 (python3 -m lab setup)`을 찍고 개발 요약은 계속(자동 재시도는 setup 성공 전까지 안 함). 다른 인터프리터는
  `LAB_MS1_PY`. NUMBA_CACHE_DIR = `LAB_CACHE/numba`. MS1 코드(std·numba)는 lab·판정 프로세스에 import하지 않고 배치마다
  작업자 프로세스 1개(`lab/ms1.py serve`)에서만 돎(모듈 이름 충돌 방지).
- **버전 고정**: std.py sha256 앞 12자리 `ee4de887037c`, gate.py `8bf8531428cb`가 아니면 `MS1 기준 변경됨`(숫자 없음).
- **속도**: 작업자 시작 처음 한 번 ~30 s(numba 컴파일·s0.85 기준값 저장), 그 뒤 ~10 s(개발 요약과 겹쳐 돎). 명세당 1~12 s
  (경로 500개 DSL 계산; macro 명세는 path·glued 따로 1000개; plugin은 경로마다 fork라 ~10~20 s). 판정(quick/full)과 동시에
  계산. 결과는 원장에 (해시, 엔진 버전 + std/gate sha)로 저장 → 다시 돌리면 즉시(G1 보정은 그때의 N으로 다시 계산).
- **봉인**: 기준 경로·G1 틀·라벨의 원래 날짜는 모두 ≤2014-12-31(시험), macro 파일도 ≤2014, measure_series는 그 뒤 행을 버림.

판정 BAR_VERSION 3 / 개발 요약 DEV_VERSION 2: rp 풀이, invvol 시작, plugin 격리, 절단 위치, 개발 엔진 재조정이 바뀌어서
예전에 저장된 판정·개발 결과는 다시 계산함(해시·계열 N은 그대로).

v1과 달라진 점: weekly/monthly `rebalance`가 기간 **마지막** 거래일 → **첫** 거래일 표본으로 바뀜(옛 방식은 다음 날짜를
알아야 해서 판정 인과성 시험에 걸림). 그래서 weekly/monthly 명세는 해시가 새로 생김(daily 명세 해시는 그대로).
