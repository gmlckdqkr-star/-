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
