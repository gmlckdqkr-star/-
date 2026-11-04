# HY1 독립 검증 기록 (2026-11-04 06:10~06:27Z)

별도 검증자가 자기 코드로 HY1 수치를 다시 계산한 스크립트와 기록이다. 결과 요약은 `../RESULT_HY1_KO.md`의 '검증' 절.
- 스크립트는 작업 당시 임시 폴더(세션 scratchpad/verify/)에 자료 파일(npz)과 numba 캐시를 썼다. 다시 돌리려면 맨 위 경로(OUTD, NUMBA_CACHE_DIR)를 바꾸고 `s1_data.py`부터 돌린다.
- `hy_info.py`·`hy_ladder.py`는 불러오기만 해도 실험 전체를 다시 돌리므로 이 스크립트들은 필요한 함수를 복사해 쓴다.
- 먼저 볼 것: `s6_ladder.log` (사다리 잡음 모형 비교), `s4_path.log` (CPPI 재생 시험).
