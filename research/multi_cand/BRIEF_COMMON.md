# MC1 작업자 공통 지침 (반드시 먼저 읽기)

## 규칙
1. 공통 사전등록: /mnt/project-files/research/multi_cand/PRECOMMIT_MC1.md (sha e4922f4b…). 채택 기준·차감 규칙은 바꾸지 않는다.
2. 내 가설 목록을 자기 폴더의 PRECOMMIT_W?.md 에 먼저 쓰고 `sha256sum` 결과를 PRECOMMIT_W?.sha256 에 남긴 뒤에만 실행한다. 실행 중 추가는 ADDENDUM_W?.md 에 시각과 이유를 적고 시도 수 N에 넣는다.
3. 자료는 2014-12-31까지만. 2015년 이후 자료·수치는 만들지도 보지도 않는다.
4. **금지 파일 (열지 말 것):** reports/best_results_summary_*, research/deep/, research/audit/, 모든 diag/ 폴더, research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md 와 results/holdout_once.csv, research/user_v104/RESULT_V104_KO.md 와 results/, research/user_v107/RESULT_V107_KO.md 와 results/, research/user_port4/RESULT_KO.md 와 results/hist.json, results_check_actual.json, research/user_v107/unseen/ (RESULT_U1_KO.md, results/, verify/), research/user_v107/final/, research/user_v107/SHARE_V107_vs_s085_KO.md, research/c3_stock_combo/, research/c3_create/fwd/, research/s085_contra/holdout/, tools/s085_now/out/, tools/s085_now/cache/, 각 레인의 holdout/ 폴더와 ho*.py 실행 결과. lab 코드가 내부에서 research/deep/lib 를 불러 쓰는 것은 괜찮지만 그 폴더를 직접 열지 않는다.
5. lab 먼저: /mnt/project-files/research/lab/USAGE_FOR_THREADS_KO.md 를 읽고 따른다. lab 코드 수정 금지. 명세에는 family(아래 지정)와 known(0~3)을 쓴다. 읽는 것은 한 줄 결과와 요약표만.
6. MS1 측정: `import sys; sys.path.insert(0,'/mnt/project-files/research/measure_std'); import std; T = std.measure(name, make, verbose=False)` (make(ctx) -> (B, bfn, bp, fstep[, engine_kw]); 예시 /mnt/project-files/research/raw_core/code/ablate.py). 환경은 이미 설치됨(numba 등). 첫 호출 약 45초. 판정 수치는 std 값이 있으면 std 값으로.
7. 아이디어 사전 점검: `python3 /mnt/project-files/tools/idea_check/idea_check.py check "아이디어"`. 키워드만 겹치고 정보·기제가 다르면 이유를 표에 한 줄로.
8. 자료 함정: (a) 1970년 전 채권 흐름은 월 단위 계단(첫 거래일에 한 달치 반영) → 채권 규칙은 1955~69 제외 민감도 확인. (b) real_ndx_86_14 준비 구간에 0 수익 237일 → 확장 백분위 신호는 0 제외 민감도 확인.
9. /mnt/project-files 는 네트워크 마운트: 경로 끝에 / 를 붙이고, 폴더 전체 검색 금지, 공유 파일은 쓴 뒤 10초쯤 뒤 다시 읽어 확인. 실행 스크립트는 `bash x.sh`/`python3 x.py` 로 (chmod 무시됨). 오래 걸리는 계산은 nice -n 10 으로.
10. git 사용 금지(리드가 한다). 하위 에이전트 만들지 말 것. CPU 4개를 세 작업자가 나눠 쓴다: --workers 1~2 이하.
11. 숫자는 보수적으로: 비용·세금·청산세·지연 2일 포함, 선택 차감(공통 사전등록 3절) 적용 전 값과 후 값을 둘 다 적는다. 목표 미달을 포장하지 않는다. 확인됨/추론/미검증을 구분.
12. 결과 파일: 자기 폴더에 RESULT_W?_KO.md (한국어, 결론/결과/검증/남은 문제, 'lab 사용' 줄, 시도 수 N, idea_check 결과), results/*.json, code/. 마지막 답은 리드에게 20줄 이내 요약(핵심 수치 표 + 판정).
