# ADDENDUM M4-1 (2026-11-04 10:54Z, 통계 계산 전)

- code/m4_stats.py의 eff_n() 안 '대표 군집(ρ ≥ 0.9)' 반복을 미리 잡은 배열에 채우는 방식으로 바꿈(같은 정의·같은 순서, 속도만: 이전 코드는 열을 붙일 때마다 전체를 복사해 수십 분 걸릴 수 있었음). 통계(SPA·RW·DSR)는 아직 계산하지 않았고, 앞기간 실행(m4_run.py)은 진행 중이며 그 결과도 아직 보지 않았다.
- 새 sha256: m4_stats.py d8f2dc1c93a54a3c7847d0a1f455b3326bd1f9e4a0543f31e9ba19b3357625bf (PRECOMMIT의 11fd089f…를 대체).
- 탐색 뒤에 쓴 실행 보조 코드(규칙·지표·판정 손잡이 없음, PRECOMMIT §4·§5를 그대로 실행): code/m4_confirm.py(상위 20개 뒷기간 1회), code/m4_final.py(MS1 행).
