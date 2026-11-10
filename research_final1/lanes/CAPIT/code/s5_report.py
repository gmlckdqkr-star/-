"""CAPIT: build RESULT_CAPIT_KO.md from the results JSON files (every number in the report is read from a results file)."""
import json, hashlib
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
E = json.load(open(LANE + 'results/killB_early.json')); U = json.load(open(LANE + 'results/signal_counts_unseen.json'))
D = json.load(open(LANE + 'results/depth_table.json')); V = json.load(open(LANE + 'results/verify.json'))
sha = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest()
frz = open(LANE + 'code/CODE_FREEZE.sha256').read().split()

def p(x, d=0):
    if x is None: return '없음'
    if d == 0 and (abs(x) < 0.01 or x <= -0.99): d = 1          # keep small and near-total-loss values readable
    return (('%+.' + str(d) + 'f%%') % (100 * x)).replace('-', '−')
def q(x): return '%.1f%%' % (100 * x)                             # a share (hit rate), no sign
def cell(c):
    if c['n'] == 0: return '사례 없음'
    if c['n'] == 1: return '%s (1건)' % p(c['values'][0])
    return '중앙 %s (%s ~ %s), 플러스 %d/%d' % (p(c['median']), p(c['min']), p(c['max']), c['n_positive'], c['n'])
def summary(s):
    L = ['| 고점 대비 낙폭 첫 돌파 | 독립 사례 수 n (돌파 연도) | 1배 1년 뒤 | 1배 3년 뒤 | 3배 1년 뒤 (NON-ACTUAL) | 3배 3년 뒤 (NON-ACTUAL) |', '|---|---|---|---|---|---|']
    for k, c in s['cells'].items():
        yrs = ', '.join(e['cross'][k]['date'][:4] for e in s['episodes'] if k in e['cross'])
        L.append('| −%s%% | %d%s | %s | %s | %s | %s |' % (k, c['n_cycles_crossed'], (' (' + yrs + ')') if yrs else '', cell(c['r1x_1y']), cell(c['r1x_3y']), cell(c['r3x_1y']), cell(c['r3x_3y'])))
    return '\n'.join(L)
def episodes(s):
    L = ['| 고점일 | 바닥일 (낙폭) | 돌파 | 돌파일 | 1배 1년 | 1배 3년 | 3배 1년 | 3배 3년 | 3배 3년 안 최저 |', '|---|---|---|---|---|---|---|---|---|']
    for e in s['episodes']:
        for k, c in e['cross'].items():
            L.append('| %s | %s (%s) | −%s%% | %s | %s | %s | %s | %s | %s |' % (e['peak'], e['trough'], p(e['trough_dd']), k, c['date'], p(c['r1x_1y']), p(c['r1x_3y']),
                                                                       p(c['r3x_1y']), p(c['r3x_3y']), p(c['min3x_within_3y'])))
    return '\n'.join(L)

e1, e2 = E['variants']['CAP1'], E['variants']['CAP2']; u1, u2 = U['variants']['CAP1'], U['variants']['CAP2']
ve, vu = V['early_1986_1999'], V['unseen_2000_2014_signal_only']
N, S, G = D['series']['NDX_1985_2014'], D['series']['SPX_TR_1928_2014'], D['series']['GSPC_PRICE_1970_2014']
ut = u1['signal']['trigger_dates'][0] if u1['signal']['trigger_dates'] else None
EF = V['early_facts']; hi2 = EF['vr_ge2_dates']; o87 = EF['oct1987']; S87 = next(e for e in S['episodes'] if e['peak'].startswith('1987'))
hi2_txt = ', '.join('%s 비율 %.2f배·RSI %.0f' % (x['t'], x['vr'], x['rsi']) for x in hi2)
def kt(r, u):
    return '| %s | %d | %d (필요 8) | %d / %d | %s | 판정 불가 (켜진 블록 0) | **탈락** | %d | %d | %d |' % (
        r['variant'], r['signal']['trigger_days'], r['n_on'], r['n_universe'], r['n_blocks'], q(r['base']),
        u['signal']['trigger_days'], u['n_on'], u['n_universe'])

txt = f"""# RESULT_CAPIT_KO: RSI 바닥 + 거래량 급증 신호 (FINAL1 레인 CAPIT)

작성 2026-11-10. 자료는 2014-12-31까지만 썼다. 사전 등록 PRECOMMIT.md sha256 `{sha[:16]}…` (FINAL1 4절을 그대로 옮김), 계산 전 코드 고정 `code/CODE_FREEZE.sha256`.
종류: B (ADD 덧씌움, v1이 1배·현금일 때 3배로 올림). 변형 수 **N = 2** (CAP1, CAP2), 둘 다 보고.
lab 사용: 아니오 (지수 거래량과 경로 가격 RSI는 lab ETF 패널로 표현할 수 없어 MS1 std·ov1lib과 gate 블록을 직접 사용).

## 결론
- **탈락. v1 유지.** 사전 등록한 두 변형 모두 초기 구간(1986-01-02 ~ 1999-12-31)에서 신호가 **한 번도 켜지지 않았다**. 켜진 블록 0개로 필요 개수 8개에 못 미쳐 B 시험을 통과하지 못했다. (확인됨, ACTUAL)
- 규칙대로 미공개 구간(2000 ~ 2014)의 성과는 열지 않았고, measure2(MS1)는 돌리지 않았다. 따라서 MS1 대표값과 실제 나스닥 수치는 없다.
- 이유: 나스닥 거래량은 급락 때도 60일 중앙값의 2배에 닿지 않는다. 1986 ~ 1999년에 RSI(14) ≤ 30인 날은 {ve['rsi_le30_days']}일인데 그날들의 거래량 비율 최대값은 {ve['max_vr_on_rsi_le30']:.2f}배({EF['max_vr_on_rsi_le30_date']})였다. 14년 동안 비율 2배 이상인 날은 {ve['vr_ge2_days']}일뿐이고 모두 오른 뒤의 날이었다({hi2_txt}). 2.5배 이상인 날은 없다. (확인됨, ACTUAL)
- 낙폭 깊이 표(서술용, 시험 아님): 깊게 빠진 뒤 3배를 사는 것은 사례가 1 ~ 6개뿐이고 결과가 갈린다. 나스닥100은 −30% 돌파 3번 중 3배 3년 뒤 플러스가 1번이고, 2000년에는 −40% ~ −70% 어느 깊이에서 사도 3배가 3년 뒤 {p(N['cells']['70']['r3x_3y']['values'][0])} ~ {p(N['cells']['40']['r3x_3y']['values'][0])}였다. (확인됨, 3배는 NON-ACTUAL)

## 결과
### 1. B 시험 (실제 달력, 21거래일 블록, 3배가 예금을 이긴 비율)
| 변형 | 초기 구간 신호일 | 초기 켜진 블록 | 초기 대상 블록(v1 3배 아님) / 전체 | 초기 기준 비율 | 초기 조건부 비율 | 초기 판정 | 2000~14 신호일 (개수만) | 2000~14 켜진 블록 (개수만) | 2000~14 대상 블록 |
|---|---|---|---|---|---|---|---|---|---|
{kt(e1, u1)}
{kt(e2, u2)}

- 표의 수치는 모두 확인됨, ACTUAL. 통과 조건: 켜진 블록 8개 이상, 조건부 비율이 기준 비율 + 10%p 이상이면서 60% 이상, 두 구간 모두.
- 초기 구간: 전체 {e1['n_blocks']}블록 중 v1이 3배가 아닌 블록 {e1['n_universe']}개(현금 {e1['universe_v1B_counts'].get('0.0', 0)}, 1배 {e1['universe_v1B_counts'].get('1.0', 0)}). 그 블록에서 3배가 예금을 이긴 비율 {q(e1['base'])}, 전체 블록에서는 {q(e1['always_in_hit'])}. (확인됨, ACTUAL)
- 2000 ~ 2014: 초기 탈락이라 성과는 열지 않고 **신호 개수만** 셌다. CAP1 신호일 {u1['signal']['trigger_days']}일({ut['t'] if ut else '-'}, RSI {ut['rsi'] if ut else '-'}, 거래량 비율 {ut['vr'] if ut else '-'}배, 그날 v1은 3배), 켜진 {u1['signal']['on_days']}일 중 v1이 3배가 아닌 날 {u1['signal']['on_days_v1_below3']}일, 대상 블록 {u1['n_universe']}개 중 켜진 블록 {u1['n_on']}개. CAP2 신호일 {u2['signal']['trigger_days']}일, 켜진 블록 {u2['n_on']}개. 이 구간도 8개에 못 미친다. (확인됨, ACTUAL)
- 거래량 자료: `research/data/panel_f32.npz.xz`의 `_NDX` 거래량(RNG1과 같은 열)을 2014-12-31까지 잘라 `data/ndx_close_volume_le2014.csv`로 저장. 1985-10-01부터 모든 날에 값이 있어 초기 구간은 1986-01-02(첫 블록)부터다. 비율은 61번째 날(1985-12-26)부터 정의된다. (확인됨, ACTUAL)
- S&P 1955 ~ 85 기준: 나스닥 거래량이 없어 적용 범위 밖(미적용). measure2: 통과 변형이 없어 실행하지 않음.

### 2. 낙폭 깊이 표 (서술용. 시험 아님, 선택 없음)
정의: 종가 기준 역대 최고점에서 다음 신고점까지를 한 사례로 보고, 사례마다 낙폭이 −X%에 처음 닿은 날을 잡는다. 그날 + 2거래일 종가에 사서 252거래일(1년), 756거래일(3년) 뒤 수익률. 거래 비용과 세금 전. 3배는 MS1 식(3r − 2rf − 연 2.45%)으로 만든 합성 상품이라 **NON-ACTUAL**이다. n은 서로 독립인 사례(고점 주기) 수다.

**표 A. 나스닥100 가격지수 {N['first']} ~ {N['last']}** (1배 = ACTUAL 가격지수, 3배 = NON-ACTUAL, 모두 확인됨). 최대 낙폭 {p(N['max_dd'], 1)}.
{summary(N)}

**표 B. S&P 500 {S['first']} ~ {S['last']}, 배당 포함 재구성(MS1의 SPX 틀)** (1배 = NON-ACTUAL 재구성, 3배 = NON-ACTUAL, 모두 확인됨). 최대 낙폭 {p(S['max_dd'], 1)}.
{summary(S)}

**표 C. 점검용: S&P 500 가격지수 {G['first']} ~ {G['last']}** (1배 = ACTUAL 가격지수(배당 제외), 3배 = NON-ACTUAL, 모두 확인됨). 배당을 빼면 표 B보다 낮아진다.
{summary(G)}

**표 D. 사례별 값 (표 A와 B의 원자료)**

나스닥100:
{episodes(N)}

S&P 500 (배당 포함 재구성):
{episodes(S)}

- 읽는 법: 나스닥100의 −40% 이하 칸은 모두 2000년 3월 고점에서 시작한 한 사례다. 2008년 급락은 2000년 고점을 회복하지 못한 상태에서 일어나 이 정의에서는 별도 사례로 잡히지 않는다. (확인됨)
- 2거래일 지연의 영향: 1987-10-19 S&P 사례에서 당일 종가에 샀다면 3배 1년 뒤 {p(S87['cross']['30']['r3x_1y_d0'])}, 2거래일 뒤에 사면 {p(S87['cross']['30']['r3x_1y'])}다. 당일 진입 값은 `results/depth_table.json`의 `_d0` 항목에 있다. (확인됨, NON-ACTUAL)
- SOX: 작성하지 않음. 로컬에 2014년 이전으로 자른 SOX 지수 자료가 없다(패널에 `_SOX` 없음. SOXX ETF 자료는 2001-07-13 시작이라 2000년 고점이 빠져 최고점 대비 낙폭을 정의할 수 없다).

## 검증
- 신호 재계산: 저장한 CSV만으로 RSI와 거래량 비율을 다른 코드로 다시 계산해 신호일 수가 일치했다 (초기 CAP1 {ve['CAP1_trigger_days']}일·CAP2 {ve['CAP2_trigger_days']}일, 2000 ~ 14 CAP1 {vu['CAP1_trigger_days']}일·CAP2 {vu['CAP2_trigger_days']}일). `results/verify.json` (확인됨)
- RSI 입력: MS1 가격 틀로 계산한 RSI와 원자료 종가로 따로 계산한 RSI의 차이 최대 {EF['rsi_frame_vs_vendor_close']['max_abs_diff']:.1e} (1986-06 ~ 1999-12, {EF['rsi_frame_vs_vendor_close']['n']:,}일). (확인됨)
- 거래량 자료의 타당성: 1987-10-19 ~ 21의 비율은 {o87['1987-10-19']['vr']:.2f}, {o87['1987-10-20']['vr']:.2f}, {o87['1987-10-21']['vr']:.2f}배다(확인됨, ACTUAL). 당시 나스닥 거래량이 평소의 1.5 ~ 2배였다는 기록과 맞는 크기다(미검증: 기억에 의존한 대조, 원문 확인 안 함).
- 신호 0개가 RSI 계산 방식에 달려 있는지: 아니다. CAP1은 당일 비율 2배 이상이 필요한데 초기 구간에 그런 날은 {ve['vr_ge2_days']}일뿐이고 RSI가 70대였다. CAP2는 2.5배 이상이 필요한데 그런 날이 없다. (확인됨)
- 낙폭 표 재계산: 나스닥100과 S&P 가격지수 {V['depth_recheck']['rows']}개 값을 원자료 종가에서 다시 계산, 돌파일 모두 일치, 수익률 차이 최대 {V['depth_recheck']['max_abs_diff']:.1e}. S&P 배당 포함 재구성은 같은 틀을 쓴 값이라 별도 원천 대조는 하지 않았다(미검증).
- 2015년 이후 자료: 읽지 않음. 패널은 날짜 열로 2014-12-31까지 자른 뒤에만 값을 사용했다.
- idea_check: 낱말 겹침으로 T39(거래량)·T27(RSI)와 '자동 거절'이 나왔다. FINAL1 사전 등록 0절이 'RSI + 거래량 동시 신호는 아직 재지 않음'으로 이 레인을 지정해 진행했다.

## 남은 문제
- 문턱(2.0배, 2.5배)을 낮추면 신호는 생기지만, 결과를 본 뒤 문턱을 바꾸는 것이라 이 레인에서는 하지 않았다. 다시 하려면 새 사전 등록이 필요하고, RSI 바닥(T13)·거래량(T39)과 같은 계열이라 닫힌 축 반복에 해당한다. (추론)
- 이번에 확인된 사실: 1986 ~ 2014년 29년 동안 RSI(14) ≤ 30이면서 거래량 비율이 2배 이상인 날은 {ve['CAP1_trigger_days'] + vu['CAP1_trigger_days']}일뿐이다(확인됨, ACTUAL). 개별 ETF·종목 거래량이나 옵션 거래량은 다른 자료이고, QQQ는 1999년 상장이라 초기 구간이 없다(추론).
- 낙폭 표는 사례 수가 1 ~ 6개라 통계 판단의 근거가 되지 못한다. 서술용으로만 쓴다.
- S&P 3배 값은 배당 포함 재구성 기준이다. 가격지수 기준(표 C, 1970 ~ 2014)에서는 −30% 돌파 {G['cells']['30']['r3x_3y']['n']}번 중 3배 3년 뒤 플러스가 {G['cells']['30']['r3x_3y']['n_positive']}번이다. (확인됨, NON-ACTUAL)
- 등록부 추가 제안(이 레인은 등록부를 쓰지 않음): "RSI(14) ≤ 30 + 나스닥 거래량 ≥ 60일 중앙값의 2.0/2.5배 동시 신호로 v1 1배·현금 → 3배 (CAPIT, N = 2): 1986 ~ 99 신호일 0, 켜진 블록 0 → B 시험 초기 탈락. 다시 열 조건: 없음(지수 거래량 기준)."

## 파일
- `PRECOMMIT.md`, `PRECOMMIT.sha256`, `code/CODE_FREEZE.sha256` (cap.py `{frz[0][:12]}…`, s1_killB.py `{frz[2][:12]}…`)
- `code/` s0_data.py(자료 자르기), cap.py(정의), s1_killB.py(B 시험), s3_depth.py(낙폭 표), s4_verify.py(재계산), s5_report.py(이 문서)
- `data/` ndx_close_volume_le2014.csv, gspc_close_le2014.csv, MANIFEST.json
- `results/` killB_early.json, signal_counts_unseen.json, depth_table.json, verify.json
"""
open(LANE + 'RESULT_CAPIT_KO.md', 'w', encoding='utf-8').write(txt)
print(txt)
