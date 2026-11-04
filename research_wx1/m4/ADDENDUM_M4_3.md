# ADDENDUM M4-3 (2026-11-04 10:58Z, MS1 행 계산 중)

- code/m4ms1.py: lab/lab/ms1eng.py를 importlib로 읽을 때 sys.modules에 이름('m4_ms1eng')을 등록하는 한 줄을 넣음. 이유: 일치 시험 때 lab measure_series 작업자가 같은 numba 캐시 폴더에 남긴 캐시를 동적 모듈이 읽다가 `No module named '<dynamic>'`로 멈춤. 계산 내용은 그대로(커널 코드는 lab 원본, 캐시 파일만 지우고 다시 컴파일). 판정 손잡이·지표 변경 없음.
- 새 sha256: m4ms1.py (RESULT의 '코드' 절에 적음).
