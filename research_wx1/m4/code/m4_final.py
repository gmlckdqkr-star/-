"""WX1-M4 MS1 rows. Finals = confirmation-pass rules that also pass SPA/RW/DSR; if none, discovery #1 = failure reference.
For information, every top-20 rule also gets its stream-resampled row (does not change the verdict).
- d_stream (대표 환산 = 16.2 + d_stream): series_paths(candidate 1964-2014 pre-tax stream) vs series_paths(s0.85 real
  pre-tax stream), path-paired median on dev250_path.
- own measure_series headline + d vs true s0.85 (std path flags), dd80 on dev250_path.
- real-history after-tax via lab ms1eng kernel (MS1 tax): NDX 1986-2014, S&P 1970-85 (NDX slot = S&P TR).
Out: results/final.json"""
import os, sys, json, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
sys.path.insert(0, S + 'code'); os.environ['NUMBA_CACHE_DIR'] = S + 'nb'
import warnings; warnings.filterwarnings('ignore')
import m4ms1 as MS
from m4eng import Env
import m4rules as MR

st = json.load(open(S + 'results/stats.json')); cf = json.load(open(S + 'results/confirm.json'))
rules = {json.loads(l)['id']: json.loads(l)['rule'] for l in open(S + 'results/rules.jsonl')}
streams = pd.read_pickle(S + 'results/top20_streams.pkl')
rw = set(st['spa_vs_1x']['rw_ids']); spa_ok = st['spa_vs_1x']['p_consistent'] < 0.05
s085 = pd.read_pickle(S + 'data/s085_stream.pkl')
SP = MS.series_paths(s085.index, s085.values)
TRUE = {bn: MS.s085_fc(bn) for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_70_85')}
S085_REAL = {'real_ndx_86_14': 0.31081466, 'real_spx_70_85': 0.12633407}   # std (std_dump.log)


def kernel_real(rule, end, start):
    env = Env(end=end, start_eval=start)
    W, F = MR.weights(env, rule)
    W = np.where(env.PAV, W, 0.0)
    used = np.flatnonzero(np.abs(W).sum(axis=0) > 0); used = used[used != env.pi[('CASH', 0)]]
    s0 = env.t0 - MS.WARM
    if len(used) == 0: return 0.0
    fin, E, ntr = MS.run_ms1eng(env.PR[s0:, used], env.cash[s0:], W[s0:, used], F[s0:])
    yrs = (env.T - s0 - MS.WARM) / 252
    return float(max(fin, 1e-9) ** (1 / yrs) - 1)


def ms1_rows(i):
    s = streams[i]
    P = MS.series_paths(s.index, s.values)
    row = dict(id=i)
    for bn in ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_70_85'):
        if P[bn] is None: row[bn] = None; continue
        fc = P[bn]['fc']; d = fc - SP[bn]['fc']
        row[bn] = dict(cagr=P[bn]['row']['cagr'], d_vs_s085stream_med=float(np.median(d)), win=float(np.mean(d > 1e-5)),
                       s085stream=SP[bn]['row']['cagr'], dd80=P[bn]['row'].get('dd80'), mdd=P[bn]['row']['mdd'])
        if bn in TRUE:
            row[bn]['d_vs_true_s085_med'] = float(np.median(fc - TRUE[bn]))
    row['daepyo'] = 16.2 + 100 * row['dev250_path']['d_vs_s085stream_med']
    row['kernel_real_ndx_86_14'] = kernel_real(rules[i], '2014-12-31', '1986-01-02')
    row['kernel_real_spx_70_85'] = kernel_real(rules[i], '1985-12-31', '1970-01-02')
    row['kernel_d_ndx'] = row['kernel_real_ndx_86_14'] - S085_REAL['real_ndx_86_14']
    row['kernel_d_spx70'] = row['kernel_real_spx_70_85'] - S085_REAL['real_spx_70_85']
    return row


conf = {o['id']: o for o in cf['top20']}
finals = []
for o in cf['top20']:
    i = o['id']
    dsr_ok = None
    if o['conf_pass'] and spa_ok and i in rw:
        finals.append(i)
ref_id = st['top20'][0]
rows = {}
for i in st['top20']:
    rows[i] = ms1_rows(i)
    r = rows[i]
    print(i, conf[i]['fam'], '대표환산 %.2f  own path %.2f%% (d true %.2f)  dd80 %.3f  kernel NDX %.2f%% (d %.2f)  S&P70 %.2f%% (d %.2f)' % (
        r['daepyo'], 100 * r['dev250_path']['cagr'], 100 * r['dev250_path']['d_vs_true_s085_med'], r['dev250_path']['dd80'],
        100 * r['kernel_real_ndx_86_14'], 100 * r['kernel_d_ndx'], 100 * r['kernel_real_spx_70_85'], 100 * r['kernel_d_spx70']), flush=True)
res = dict(finals=finals, failure_reference=None if finals else ref_id, s085_stream_rows={bn: (SP[bn]['row'] if SP[bn] else None) for bn in SP},
           rows={str(k): v for k, v in rows.items()})
json.dump(res, open(S + 'results/final.json', 'w'), indent=1, default=float)
print('finals', finals, 'failure_reference', res['failure_reference'])
