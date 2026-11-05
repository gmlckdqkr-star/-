# NX1 사전등록 (2026-11-05, 결과 보기 전 잠금)

목적: v1(s0.85, MS1 16.2%)을 넘는 새 축 찾기. 닫힌 축 70여 개(tools/idea_check/closed_axes.json)와 겹치지 않는 축만, 싼 kill 시험부터.
금지 파일(열지 않음): reports/best_results_summary_*, research/deep/, research/audit/, diag/, research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md + results/holdout_once.csv, research/user_v104|v107 결과, research/user_port4 결과, research/c3_stock_combo/, research/c3_create/fwd/, research/s085_contra/holdout/, research/theory_sim/holdout/, tools/s085_now/out|cache/.
자료: 2014-12-31까지만.

## K1 실행 구조 (신호 변경 아님)
v1 그대로, 엔진 조건만 바꿈. MS1 std.measure 5기준.
- K1a 체결 지연 1일 (종가 신호 → 다음 거래일 체결; 프로그램이 다음 미국 장 시작에 주문하는 현실값에 가까움)
- K1b 현금 이율 차감 1%p (MS1은 단기금리−2%p; 외화 RP·초단기채 대용, 낙관 쪽 민감도)
- K1c 체결 지연 3일 (스트레스, 판정에는 안 씀)
판정: '문' = K1a 또는 K1b가 헤드라인 +1.0%p 이상이고 실제 NDX·SPX 3기준 모두 ≥ 0. 이 값은 MS1 대표값을 바꾸지 않고 '조건 민감도'로만 보고.

## K2 새 정보: 기술 산업 경기 (Fed G.17 생산지수)
원자 4개 (trials=4로 G1 디플레이션):
- A1: IPG3344S(반도체·전자부품 생산) 3개월 평균의 전년비 > 0 → 3배, 아니면 현금
- A2: A1 전년비의 6개월 변화 > 0 (가속)
- A3: IPG334S(컴퓨터·전자제품 생산) 3개월 평균 전년비 > 0
- A4: A3 가속
발표 지연: 관측월 m 값은 m+2 첫 거래일부터 사용.
주의: ALFRED 빈티지가 2015-02부터만 있어 최신 수정치를 씀 → 정보량이 실제보다 많을 수 있는 '낙관 상한' 시험. 그래서 실패는 확정 kill, 통과는 빈티지 문제를 풀기 전까지 채택 불가.
판정: gate.test (NDX 1986-2014, SPX 1955-85 중 낮은 쪽, 디플레이션) ≥ 0.65 HOLD 이상이면 생존, 아니면 CLOSE.
같은 계열 추가 변형 없음.

## 실패 시
새 축 하나로 1회 재계획 후, 그것도 실패면 소진 메모로 닫음.
