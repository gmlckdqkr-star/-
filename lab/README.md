# 연구 실험실 (lab) — v1

전략 아이디어를 **짧은 명세 파일(YAML 10~20줄)** 로 쓰면, LLM 없이 로컬에서
개발 구간 요약(≤2014) → 프로젝트 기준 판정 코드(blackbox2 + d6q)로 판정 → 원장 기록까지 하고 **결과를 한 줄**로 돌려줍니다.

## 실행
```
python3 -B -m lab run specs/trend_tqqq_200.yaml specs/qld_088_hold.yaml            # --bar quick (기본)
python3 -B -m lab run specs/x.yaml --bar full [--workers 4] [--all-versions]
python3 -B -m lab run specs/x.yaml --bar none                                       # 개발 요약만
python3 -B -m lab ledger
python3 -B tests/test_parity.py      # 기존 beat_qld 엔진과 결과 일치 (따로 실행)
python3 -B tests/test_bb.py          # 기준 어댑터 시험 (따로 실행: 두 시험이 서로 다른 engine 모듈을 씀)
```
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
  합집합(엄격 쪽, lab 해석). 인과성 = 실제 경로(고정 3 + 무작위 40 절단) + 부트스트랩 2경로(무작위 40 절단씩), quick에서도 부트스트랩 2경로.
- `none` — 개발 요약만.
- 판정 가능한 상품: QQQ(→QQQM), QLD, TQQQ, SSO, UPRO, TMF, SPY, TLT, IEF. 그 밖의 상품(SOXL, GLD, SHY …)은
  공통 원천 대용이 없어 `REJECT (version impossible)`.
- 판정 경로의 규칙: 경로마다 명세를 다시 계산(합성 가격), 실제 과거 시세 읽기 차단, 비중은 합 ≤0.88·Σ배율×비중 ≤2.64로 축소,
  워밍업 300일(더 긴 되돌아보기는 처음에 비어 있음), 합성 경로의 month()/weekday()는 의미 없음,
  명세의 `delay`는 판정에 안 씀(중개 지연 0: 종가 결정 → 다음날 시가 체결).
- 명세 검사: `delay`는 정수 ≥2만 허용(그보다 작으면 같은 봉/미래 체결), `cost`는 0.003 미만이면 0.003으로 올림
  (판정 쪽은 비교 기준 QQQM/QLD 보유에도 같은 비용이 들어감).
- 코드에 "lab interpretation, bar owner not yet confirmed" 라고 적힌 곳은 기준 담당 확인 전의 lab 해석.

## 봉인 (코드로 강제)
- 모든 시뮬레이션은 src_end='2014-12-31'을 명시해서 실행. 경로 생성기를 감싸서 그 뒤 날짜로는 생성 자체가 안 됨.
- 2015년 이후 구간은 계산·출력·저장하지 않음. 예전 MVP의 봉인 구간 PASS/REJECT 판정과 계열별 횟수 예산은 삭제.
- 개발 요약(≤2014 실제 자료 + 짝 재표본)은 **개발 선별 (기준 아님)** 표시만 함.
- 같은 명세(해시 같음)는 다시 계산하지 않음. 계열별 시험 수 N을 셈. 기준 결과는 (해시, 단계)별로 저장.

## DSL
`price sma ema ret vol high low dd rsi month weekday min max abs lag latch`. `latch(on, off)`: on이면 켜짐,
off면 꺼짐, 아니면 전날 상태 유지, 처음엔 꺼짐, 같은 날 둘 다면 off.
창·지연 인자(`sma ema ret vol high low dd rsi lag`)는 정수 ≥1만 허용(0·음수는 미래 행을 읽으므로 오류).
따옴표 이름(`price('XLK')`)도 판정 경로에 없으면 `REJECT (version impossible)`.
