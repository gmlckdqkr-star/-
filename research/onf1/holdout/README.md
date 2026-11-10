# research/onf1/holdout/ : 설계 스레드는 열지 마세요

이 폴더에는 2015년 이후 성과 수치가 들어 있습니다 (전체 보고서, 실제 주문 순서 표, 2015년 이후 확인 결과 2건(`hist_holdout.json`, `hist_extra_holdout.json`), 병렬 검증 기록, 2015년 이후 원자료).
프로젝트 규칙(FORBIDDEN FILES)에 따라 전략을 설계·선택하는 스레드는 이 폴더를 읽지 않습니다.
설계에 쓸 수 있는 것은 상위 폴더의 `RESULT_ONF1_KO.md`, `PROGRAM_SPEC_ONF1_KO.md`, `PRECOMMIT_ONF1.md`, `code/`, `results/`, `data_cut/` 입니다.
