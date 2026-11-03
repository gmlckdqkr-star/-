# lab 사용 규칙 (연구 스레드용, 2026-11-03)

목적: 백테스트 코드를 매번 새로 쓰지 말고 짧은 명세로 돌려 토큰을 줄인다. 계산과 검증은 로컬에서 하고, LLM은 아이디어와 판단만 맡는다.

## 언제 쓰나
- 가격 패널(research/data/panel_f32.npz.xz)로 표현되는 전략이면 **먼저 lab**을 쓴다. 추세, 변동성, 회전(top-k), 역변동성/위험균형, 상태 래치, 손실 브레이크, 격자 탐색, 국내 ETF 계좌(account: kr_etf)가 여기에 해당한다.
- DSL로 안 되는 모양은 plugin(파이썬 함수 1개, 격리 실행)으로 쓴다.
- 대상: 미국 상장 ETF 22종(그중 QQQ·QLD·TQQQ·SSO·UPRO·TMF·SPY·TLT·IEF는 기준 판정까지), 국내 지수 ETF 4종(KR200·KRLEV·KRINV·KRSEMI, account: kr_etf, 개발 요약만). 개별 종목은 미국·국내 모두 아직 없다.
- 패널에 없는 비가격 자료(EDGAR, 거래량 외 재무, 뉴스 등)는 아직 lab에 넣을 수 없다. 이런 경우에만 직접 코드를 쓰고, 이유를 보고에 한 줄로 적는다.

## 실행 (복사해서 쓰기)
```
cd /mnt/project-files/research/lab
python3 -B -m lab run <명세.yaml 또는 폴더> --bar quick     # 빠른 선별(기준 아님), 명세당 5~15초
python3 -B -m lab run <명세> --bar full --workers 4          # 기준 판정(약 2분, 첫 REJECT에서 멈춤)
python3 -B -m lab ledger                                     # 계열별 시험 수 N
```
- **읽는 것은 한 줄 결과와 요약표만** 읽는다. 상세 JSON(var/out/)은 필요할 때만 연다.
- 문법은 README.md의 "DSL 요약표"를 보고, 예시는 specs/와 specs/examples/를 본다.
- 명세에는 family(계열)와 known(0~3, 알려진 정도)을 반드시 쓴다. 격자 점 하나하나가 N에 들어간다.

## 결과 해석
- 판정 이름은 REJECT / Q60 미달 / PENDING(통합 담당 대기) / 판정 불가뿐이다. lab은 APPLY를 내지 않는다.
- quick은 선별일 뿐이고 기준 판정이 아니다. 보고하는 최종 수치는 여전히 MS1 기준(research/measure_std)으로 낸다.
- lab은 2014-12-31 이후를 계산하지 않는다(코드로 강제). 2015년 이후 수치는 lab에서 나오지 않는다.
- 판정 경로가 재표본하지 않는 입력(_IRX 등 거시, *.KS, KRW_X, GLD, SHY)과 대용 없는 상품(SOXL 등)은 기준에서 `REJECT (version impossible)`로 나온다. 개발 요약은 계산된다.
- account: kr_etf는 개발 요약만 낸다(편도 13bp, 해외지수 ETF는 매도 건별 15.4% 손실 상계 없음, 국내주식형 ETF는 비과세 가정). 기준 칸은 "판정 불가"로 나온다.

## 보고에 꼭 넣을 한 줄
- `lab 사용: 예 (명세 N개, 계열 이름)` 또는 `lab 사용: 아니오 (이유: 예) 패널에 없는 EDGAR 자료)`. 이 줄로 규칙을 지켰는지 확인한다.

## 하지 말 것
- lab 코드는 내부에서 research/deep/lib과 signal_research_v3의 판정 코드를 불러 쓴다. 스레드가 그 폴더를 직접 열면 안 된다(금지 목록은 그대로 유지).
- lab/ 아래 코드를 고치지 말고, 필요한 기능은 'lab' 스레드에 요청한다. 원본은 저장소 브랜치 claude/project-thread-cbs1hc의 lab/에 있다.
