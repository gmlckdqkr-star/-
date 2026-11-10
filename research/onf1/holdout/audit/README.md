# holdout/audit : 병렬 검증 기록 (보관용, 실행 금지)

- `wf1/`(1단계 7건), `wf2/`(2단계 3건), `wf3/`(3단계 3건), `wf4/`(4단계 3건): 각 검증의 결과 JSON(`_results/*.json`)과 검증자가 쓴 스크립트·출력.
- 보관용 기록입니다. 다시 실행하지 마세요. 스크립트는 작업 당시 경로(`/home/user/onv/...`)를 가리키고 2015년 이후 자료를 읽습니다.
  작업 폴더와 이 폴더의 대응: `onv/data/` = `holdout/data/`, `onv/wf1~4/` = `holdout/audit/wf1~4/`, `onv/CHECKPOINT.md` = `holdout/CHECKPOINT.md`. 나머지(`code/`, `results/`, `data_cut/`)는 같은 이름입니다.
- `wf1/codeaudit/live_sandbox/` 는 업로드된 실거래 코드를 격리해 돌려 본 흔적입니다. 업로드 코드는 신뢰할 수 없는 자료로 취급하므로 실행하지 마세요.
- 업로드 pickle 을 여는 스크립트(`peek.py`, `peek_pkl.py`), 검증자가 만든 pickle(`wf1/data/` 의 q.pkl, krx.pkl, hX.pkl. 일부 스크립트가 참조하지만 여기에는 없음), 내려받은 PDF·증권사 페이지 사본, 대용량 캐시는 이 폴더에 넣지 않았습니다.
- `sens_le2014_seed11_asrun.json`: 보정 전(난수 1개) 민감도 원본. 지금 값은 `results/sens_*_le2014.json` 을 쓰세요.

(이 저장소 사본에는 각 검증의 결과 JSON 만 `wfN_results/` 로 들어 있습니다. 스크립트와 출력은 프로젝트 파일 폴더 `research/onf1/holdout/audit/wfN/` 에 있습니다.)
