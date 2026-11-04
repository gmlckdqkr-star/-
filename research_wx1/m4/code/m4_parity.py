"""WX1-M4 parity tests (before the search):
P1 my pre-tax engine run_pre == lab ms1eng.run1(tax 0, harvest 0) on identical inputs (3 specs).
P2 MS1 real NDX after-tax via lab's kernel on MS1-frame inputs: trend_tqqq_200 = 6.08 % (MS1/lab locked), TQQQ hold 3.87 %.
P3 my data (m4_base) vs MS1 frame: NDX/rf/cash identical on 1986-2014; trend_tqqq_200 built from my Env (SMA warm-up
   from my NDX slot) through lab's kernel.
P4 my series_paths == lab ms1.measure_series (worker) for two streams (1x NDX from my data, s0.85 pre-tax stream).
Output: results/parity.json"""
import os, sys, json, time, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
sys.path.insert(0, S + 'code')
os.environ['NUMBA_CACHE_DIR'] = S + 'nb'
import m4ms1 as MS
from m4eng import Env, run_pre
res = {}
X = MS.frames()['ndx']
i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - MS.WARM
Xr = X.iloc[i0:]
r = Xr['r'].values; rf = Xr['rf'].values; p = Xr['p'].values
cash = np.maximum(rf - 0.02 / 252, 0.0) * (1 - 0.154)
tq = 3 * r - 2 * rf - 0.0245 / 252; qq = r - 0.002 / 252; ql = 2 * r - rf - 0.0245 / 252
sma = pd.Series(p).rolling(200, min_periods=200).mean().values
up = (p > sma).astype(float)                       # NaN sma -> False -> cash (lab DSL)
T = len(r); yrs = (T - MS.WARM) / 252
mfirst = np.r_[True, Xr.index.to_period('M')[1:] != Xr.index.to_period('M')[:-1]]
specs = {
    'trend_tqqq_200': (np.c_[tq], np.c_[up], np.zeros(T, bool)),
    'tqqq_hold': (np.c_[tq], np.ones((T, 1)), np.zeros(T, bool)),
    'qqq50_tqqq50_monthly': (np.c_[qq, tq], np.c_[np.full(T, .5), np.full(T, .5)], mfirst),
    'qld_088_hold': (np.c_[ql], np.full((T, 1), 0.88), np.zeros(T, bool)),
}
for nm, (R, W, F) in specs.items():
    fin0, E0, _ = MS.run_ms1eng(R, cash, W, F, tax=0.0, harvest=0)
    Em, ntr = run_pre(np.ascontiguousarray(R), cash, np.ascontiguousarray(W), F, MS.WARM, 2, 0.003)
    fin, E, ntr2 = MS.run_ms1eng(R, cash, W, F)
    res[nm] = dict(pretax_maxabs_diff=float(np.max(np.abs(Em - E0))), pretax_cagr_mine=float(Em[-1] ** (1 / yrs) - 1),
                   pretax_cagr_lab=float(E0[-1] ** (1 / yrs) - 1), aftertax_real_ndx_lab_kernel=float(max(fin, 1e-9) ** (1 / yrs) - 1),
                   trades=int(ntr))
    print(nm, res[nm], flush=True)
# P3: my data vs MS1 frame
env = Env(end='2014-12-31', start_eval='1986-01-02')
d = env.idx
a = pd.Series(env.u[:, env.ai['NDX']], index=d).loc['1986-01-02':]
b = pd.Series(X['r'].values, index=X.index).loc['1986-01-02':]
rr = pd.Series(env.rf, index=d).loc['1986-01-02':]; rb = pd.Series(X['rf'].values, index=X.index).loc['1986-01-02':]
j = a.index.intersection(b.index)
res['data_ndx_maxabs'] = float(np.max(np.abs(a.reindex(j).values - b.reindex(j).values)))
res['data_rf_maxabs'] = float(np.max(np.abs(rr.reindex(j).values - rb.reindex(j).values)))
res['data_days_mine_vs_ms1'] = [int(len(a)), int(len(b)), int(len(j))]
# trend_tqqq_200 from my Env (NDX slot = SPX TR before 1986 -> SMA warm-up differs in 1986 only)
t0 = env.t0
W = np.zeros((env.T, len(env.prods)))
upm = np.nan_to_num(env.sma_up(200)[:, env.ai['NDX']]) > 0.5
W[upm, env.pi[('NDX', 3)]] = 1.0
rm, _ = env.run_W(W, np.zeros(env.T, bool))
s0 = t0 - MS.WARM
R3 = np.c_[env.PR[s0:, env.pi[('NDX', 3)]]]; W3 = np.c_[upm[s0:].astype(float)]
fin, E, _ = MS.run_ms1eng(R3, env.cash[s0:], W3, np.zeros(len(R3), bool))
yrs3 = (len(R3) - MS.WARM) / 252
res['trend_tqqq_200_myenv'] = dict(aftertax_real_ndx=float(max(fin, 1e-9) ** (1 / yrs3) - 1),
                                   pretax_mine=float(np.prod(1 + rm) ** (252 / len(rm)) - 1))
print('myenv', res['trend_tqqq_200_myenv'], res['data_ndx_maxabs'], res['data_rf_maxabs'], flush=True)
# P4: series_paths vs lab measure_series
sys.path.insert(0, '/mnt/project-files/research/lab')
os.environ.setdefault('LAB_MS1_PY', sys.executable)
from lab import ms1 as LM
s1 = pd.Series(env.PR[t0:, env.pi[('NDX', 1)]], index=d[t0:])
s2 = MS.s085_stream()
for nm, s in (('ndx1x_myenv', s1), ('s085_pretax_stream', s2)):
    t = time.time()
    mine = MS.series_paths(s.index, s.values)
    lab = LM.measure_series(s.index, s.values, nm)
    cmp = {}
    for bn in MS.BASES:
        if mine[bn] is None or lab.get(bn) is None:
            cmp[bn] = [None if mine[bn] is None else mine[bn]['row']['cagr'], None if lab.get(bn) is None else lab[bn]['cagr']]; continue
        cmp[bn] = [mine[bn]['row']['cagr'], lab[bn]['cagr'], lab[bn]['d_vs_s085'], mine[bn]['row'].get('dd80')]
    res['series_' + nm] = cmp
    print(nm, cmp, round(time.time() - t, 1), flush=True)
json.dump(res, open(S + 'results/parity.json', 'w'), indent=1)
print('done')
