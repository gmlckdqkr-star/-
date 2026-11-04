# kr_dart — OpenDART 공시 목록 (메타데이터만), 2001-01 ~ 2014-12

- 원천: OpenDART list.json (opendart.fss.or.kr, 금융감독원 무료 API). 2026-11-04 08:16~09:30Z 수집, 스레드 '아직 안 쓴 공개 자료 넓게 찾기'.
- pblntf_ty B(주요사항보고) 2001-01부터, I(거래소공시) 2002-06 무렵부터(그 전은 원천에 없음). 1개월 창, 페이지 전부.
- 열: corp_code, corp_name(**현재 이름 = 2014년 뒤 정보, 결정에 쓰지 말 것**), stock_code, corp_cls, report_nm, rcept_no, flr_nm, rcept_dt, rm, _win(수집 창).
- API 키는 파일에 없다. 공시 시각은 없음(접수일만) → 접수일 뒤 2거래일 진입이 보수.
- 같은 공시가 [기재정정]·[첨부추가] 등으로 여러 번 나온다. 중복 정리 규칙 예: research/open_data/code/od_k.py norm().
- 2014-12-31 뒤 행 없음. 수집 코드: research/open_data/code/fetch_dart.py. sha256: MANIFEST_SHA256.txt.
