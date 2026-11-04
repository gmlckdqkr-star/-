"""M1 parity: (1) lab sleeve engine (ms1eng, MS1 sec.1 rules) pre-tax curve of trend_tqqq_200 (TQQQ / cash, SMA200 on the
NDX level) vs this lane's screening engine on the same real paths (real_ndx_86_14, real_spx_55_85); (2) the daily log
difference stream g reproduces the equity curve; (3) after-tax real NDX trend_tqqq_200 via ms1eng = lab 6.08%, and via
std.measure; (4) s0.85 std.measure numbers. Output out/parity.json."""
import os, sys, json, time, numpy as np
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, SCR + 'code'); sys.path.insert(0, '/mnt/project-files/research/lab')
import yaml
from lab import ms1, dsl
import m1_engine as EN

srv = ms1._Server()
std = srv.std
spec = dsl.check_spec(yaml.safe_load(open('/mnt/project-files/research/lab/specs/trend_tqqq_200.yaml')))
ok, el = ms1.eligibility(spec)
res = {}
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'):
    c = srv.C[bn]
    W, force = srv.weights(spec, bn, el)
    fin0, E0, tr0 = srv.run(bn, ['TQQQ'], W, force, tax=0.0)
    X = EN.products(c.r[0], c.rf[0])
    # this lane's own SMA200 signal on the path level (no lab DSL)
    lv = c.lvl[0]; cs = np.cumsum(np.r_[0.0, lv]); sma = np.full(len(lv), np.nan); sma[199:] = (cs[200:] - cs[:-200]) / 200
    mine_sig = np.where(np.isfinite(sma) & (lv > sma), 1.0, 0.0)
    sig_match = float(np.mean(mine_sig[ms1.WARM - 1:] == (W[0, ms1.WARM - 1:, 0] > 0.5)))
    dec = np.where(mine_sig > 0.5, 0, 3).astype(np.int64)
    E1 = EN.equity_from_dec(X, dec, ms1.WARM, c.T)
    rel = float(np.abs(E1 / E0[0] - 1).max())
    # g stream vs equity
    A = np.zeros((1, c.T), np.int8); A[0] = mine_sig.astype(np.int8)
    rule = np.array([0, -1, -1, 0, 0, 3, 1], np.int64)
    d2, act, g = EN.one_path(A, X, rule, c.T)
    k0 = ms1.WARM + 5
    lhs = np.log(E1[-1] / E1[k0 - ms1.WARM]); rhs = float(np.sum(g[k0 + 1:] + np.log1p(X[2, k0 + 1:])))
    # after-tax with this lane's decisions through ms1eng
    Wm = (dec == 0).astype(float)[None, :, None]
    fin_t, E_t, _ = srv.run(bn, ['TQQQ'], Wm, force, tax=ms1.TAX)
    res[bn] = dict(sig_match=sig_match, pretax_maxrel_diff=rel, pretax_cagr_lab=float(E0[0, -1] ** (252 / E0.shape[1]) - 1),
                   pretax_cagr_m1=float(E1[-1] ** (252 / len(E1)) - 1), g_vs_equity_log=lhs - rhs,
                   aftertax_cagr_ms1eng_m1dec=float(fin_t[0]))
    print(bn, res[bn], flush=True)
# std.measure on the same spec (level 3 x weight) and s0.85
def mk(c):
    lv = c.lvl; cs = np.cumsum(np.c_[np.zeros(c.P), lv], axis=1); sma = np.full(lv.shape, np.nan); sma[:, 199:] = (cs[:, 200:] - cs[:, :-200]) / 200
    return np.where(np.isfinite(sma) & (lv > sma), 3.0, 0.0), std.ident, np.zeros(1), 0.5
T = std.measure('trend_tqqq_200', mk, verbose=False)
res['std_trend'] = {k: (v['cagr'] if isinstance(v, dict) else v) for k, v in T.items()}
S = json.load(open(SCR + 'out/p0_s085.json'))
res['std_s085'] = {k: (v['cagr'] if isinstance(v, dict) else v) for k, v in S.items()}
print('std trend', res['std_trend']); print('std s085', res['std_s085'])
json.dump(res, open(SCR + 'out/parity.json', 'w'), indent=1)
