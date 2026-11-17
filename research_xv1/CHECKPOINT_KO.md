# XV1 재개 체크포인트 (2026-11-17 15:30Z 작성)

주간 사용 한도 때문에 **등록 직전**에서 멈춘 상태입니다. 다음에 이어받는 사람은 이 파일만 읽고 재개할 수 있습니다.

## 1. 현재 상태 (확인됨)

- **아무것도 등록되지 않았습니다.** `/mnt/project-files/research/xv1/` 는 비어 있고 원장(LEDGER)과 `research_xv1/registry/` 는 없습니다.
- **2014년 이후 행은 한 번도 채점하지 않았습니다.** 봉인 블록(2016-18, 2022-24) 숫자는 어디에도 계산, 출력, 저장되지 않았습니다.
- 최종본은 이 커밋의 `research_xv1/` 입니다 (평가기 `code/xv1.py` v8, 등록 문서 `PREREG_XV1_STRUCTURE.md` v8, `[[` 표시 없음).
- 1차 배치 96개 구성의 해시 요약은 `3abe326c7b3fecf4` / `8a8db77e2cb9544f` 로 v6부터 변하지 않았고, 후보 파일 5개는 모두 검사 규칙을 통과합니다.
- 등록 데이터 13개 파일의 고정 사본과 sha256: `/mnt/project-files/research/xv1_data_frozen_20261117/` (`MANIFEST.json`). 이 13개 원본 파일은 다시 쓰면 안 됩니다.
- 사용자 승인: 구조 등록은 2026-11-11 12:49Z 답변(메시지 `cmsg_013GuJ2gSecTDkpekhQ7SWhg47X7ADtvr4d67q4nBbKHKk`)으로 승인됨. 봉인 블록 개봉(G3)은 건마다 사용자 결정 카드가 따로 필요합니다 (최대 3회, 되돌릴 수 없음).

## 2. 검증 이력 요약

- v6 전체 검토 46건, v7 재검토 17건과 13건, v8b 재검토 10건, v8c 변경분 검토 4건, v8d 3인 검토 21건(중간 3, 낮음 18), 마지막 변경분 검토(치명 0, 높음 0, 중간 1, 낮음 5, 문장 6곳)까지 모두 반영했습니다.
- **한계:** 마지막 검토에 대한 답(평가기 십여 줄과 시험 추가)은 자체 시험만 거쳤고 독립 검토를 다시 받지 않았습니다. 문서 이력 문단에 그대로 적혀 있습니다.
- 자체 시험 6종 (이 사본, 등록 환경): **아래 4절에 결과를 적습니다.**

## 3. 재개 순서

1. 새 컨테이너라면: 저장소를 받고 브랜치 `claude/project-thread-0hgv07` 로 이동, 가상환경 `~/.cache/lab/ms1-venv` 준비 (`/mnt/project-files/research/lab/USAGE_FOR_THREADS_KO.md`), `mkdir -p /home/claude/pyc_xv1_reg /home/claude/nbcache_xv1_reg` (두 폴더는 비어 있어야 함).
2. 모든 실제 실행의 명령줄 (평가기가 이 환경이 아니면 거부합니다):

   ```
   cd /home/user && PYTHONHASHSEED=0 NUMBA_CACHE_DIR=/home/claude/nbcache_xv1_reg NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OPENBLAS_CORETYPE=HASWELL OPENBLAS_NUM_THREADS=1 PYTHONPYCACHEPREFIX=/home/claude/pyc_xv1_reg ~/.cache/lab/ms1-venv/bin/python -B <스크립트>
   ```

   `-B` 없이 이 PYTHONPYCACHEPREFIX 로 파이썬을 켜면 폴더에 컴파일 파일이 생겨 이후 실행이 모두 거부됩니다 (그때는 폴더를 비우면 됨).
3. 자체 시험 6종을 **읽기 전용 사본**에서 다시 돌립니다 (편집 중인 파일에서 돌리지 않음): `t_xeng_parity.py`, `t_design_acct.py`, `m_checks.py --dry2014`, `t_batch_dry.py <임시폴더>`, `t_old_end.py`, `t_g3_synth.py <임시폴더>` (마지막 것은 약 65분). 모두 exit 0, `EXPECTED VERDICTS OK`, `GUARDS OK`, `DRY RUN PASS` 여야 합니다.
4. 13개 데이터 파일의 sha256 을 `MANIFEST.json` 과 대조합니다.
5. 등록부터 1차 배치 종료까지는 **한 컨테이너 수명 안에서** 이어서 합니다 (환경 표식이 달라지면 G2와 개봉이 거부됨):
   `m_register.py` (커밋과 푸시가 안 된 상태면 스스로 거부) → `research_xv1/registry/LEDGER.jsonl` 커밋과 푸시 (이후 원장 단계마다 반복) → `m_checks.py` → `m_v1.py` → `m_batch1.py register` → `m_batch1.py run` (nohup 로 분리 실행, 약 8~10시간 추정, 중단 후 재개 가능. 한 구성에서 두 번 멈추면 그 구성은 무효가 되므로 시간 제한으로 죽이지 않음).
6. 통과 구성에 한해 G0, G2. 봉인 블록 개봉 전에는 반드시 사용자 결정 카드.

## 4. 자체 시험 결과 (이 사본)

- 15:27Z 시작, 실행 중. 끝나면 이 절을 갱신합니다. 갱신이 없으면 **미검증**으로 보고 3번을 다시 실행하세요.
- 같은 컨테이너가 살아 있으면 로그는 `/tmp/xv1_logs/v8f/` (`summary.txt`), 시험에 쓴 고정 사본은 `/tmp/xv1_verify4/v8f/` 에 있습니다.

## 4-1. 보조 도구 (`research_xv1/tools/`)

- `selftest.sh <고정 사본> <로그 폴더> <임시 폴더>`: 자체 시험 6종을 등록 환경으로 돌립니다. 실제로 쓴 실행 스크립트를 인자만 받도록 옮긴 것으로, 이 파일 자체는 아직 실행해 보지 않았습니다 (미검증).
- `cfg_digest.py <code 폴더>`: 96개 구성 해시 요약과 후보 파일 검사 결과를 출력합니다 (`96 3abe326c7b3fecf4 8a8db77e2cb9544f`, 다섯 파일 모두 `False` = 위반 없음).

## 5. 지켜야 할 규칙

- 봉인 블록 숫자는 계산, 출력, 저장, 보고 금지. 등록과 `m_checks.py` 전에는 2014년 이후 행 채점 금지.
- 1차 배치 후보는 등록된 배치 밖에서 채점하지 않습니다 (2014년 이전 자료로도 금지, 다중 검정 계수에 들어감).
- 금지 파일 목록은 프로젝트 메모리의 `forbidden-files` 를 따릅니다.
- v1 은 15.2% 로만 인용합니다. 평균이 아니라 경로별 기하 수익률의 중앙값, p10, P(-80%) 로 보고합니다.
