---
name: trading-idea-precheck
description: Before starting any new trading-strategy research idea in the 자동 매매 프로그램 project, check it against the closed-axes registry and the G1 information gate so dead ideas are rejected in one step.
---

# 매매 연구 아이디어 사전 점검

사용자가 새 매매 방법·신호·종목 고르기 아이디어를 내거나, 새 연구 레인을 열기 전에 쓴다. 목적: 이미 닫힌 축을 다시 파서 시간을 쓰지 않고, 새 축이면 같은 관문으로 빠르게 잰다.

## 1. 닫힌 축 점검 (항상 먼저)
```
python3 /mnt/project-files/tools/idea_check/idea_check.py check "<아이디어를 한 줄로>"
```
- **자동 거절**: 결과 한 줄과 근거 파일을 사용자에게 그대로 알려 준다. '다시 열 조건'을 충족하는 새 자료가 없으면 시작하지 않는다.
- **막힘**: 어떤 사용자 문(가입·로그인·유료)이 필요한지와 기대값을 한 줄로 알려 준다. 유료는 제안만.
- **전진 기록만 / 진행 중**: 해당 기록이나 스레드를 알려 준다.
- **새 축 후보**: 2단계로.
- 아이디어를 낱말만 바꿔 여러 번 넣어 보고(예: 영어 이름, 다른 표현), 가장 높은 일치를 쓴다.

## 2. 새 축이면 관문부터
1. 자료가 2014-12-31까지 있고 발표 지연을 넣을 수 있는지, 무료·합법(robots.txt·약관)인지 확인한다. Financial Datasets는 절대 호출하지 않는다. 사용자 개인정보를 외부에 넣지 않는다.
2. 금지 파일(프로젝트 메모리 forbidden-files)을 열지 않는다.
3. 사전 등록 파일(변수·변환·시도 수 N)을 먼저 쓴다.
4. 시점 신호: `research/breakthrough/code/gate.py`의 `gate.test(sig, trials=N)`. 보정 적중 65% 미만 닫음, 65~70% 보류, 70% 이상 설계. 항상 보유 적중 55.5%를 넘어야 정보가 있다.
   종목·수익원: 비용 후 단독 Sharpe 약 1.1(같은 기준 0.55), 종목 신호는 월 IC 0.05 이상 + 지속성(IS12 기준).
5. 가격 패널로 표현되면 lab 먼저: `research/lab/USAGE_FOR_THREADS_KO.md`. 보고에 `lab 사용: 예/아니오(이유)`.
6. 숫자는 MS1 대표값(dev250_path, 세후·청산세)만, 보수 점검을 모두 끝낸 뒤 한 번만 보고한다.

## 3. 끝나면 등록
결과가 무엇이든 등록부에 한 줄 추가한다:
```
python3 /mnt/project-files/tools/idea_check/idea_check.py add --id <새 id> --area <시점|종목|ETF·배분|레버리지|구조> --name "<이름>" --kw "<낱말,낱말>" --verdict <CLOSED|BLOCKED|FORWARD|OPEN> --result "<한 줄 결과>" --evidence "<결과 파일 경로>" --reopen "<다시 열 조건>"
```

## 보고 형식 (한국어)
결론 / 결과 / 검증 / 남은 문제. 확인됨·추론·미검증을 구분한다.
