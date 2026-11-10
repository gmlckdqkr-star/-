"""Look-ahead (truncation) test on the real NDX basis: rebuild the data frame, macro flags, the nine NBR base signals and the v1
engine record with the history cut at an earlier date; every value on the overlap must equal the full-sample value.
Also: summary of post-2014 checks (calendar maxima)."""
import os, sys, json
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, jp, ov, bk, rx, beng
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
import strat as S_lib
OUT = '/mnt/project-files/research/final1/verify_main/results/'
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX')
assert X.index.max() <= pd.Timestamp('2014-12-31')
i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
def ctx(Xc): return ov.Ctx(Xc, ov.flags_hist(Xc), np.arange(i0, len(Xc))[None, :])
def rec_v1(c, B):
    k = dict(beng.F1); k['fstep'] = 0.1; pp, D = beng._args(k)
    o, rec = beng.run_rec(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), np.ascontiguousarray(B[0], dtype=np.float64),
                          np.ascontiguousarray(bk.features(c)[0]), int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'],
                          pp['cspr'], pp['er3'], pp['step'], rx.av23s, np.asarray(rx.P_av23s(.85), dtype=np.float64), float(pp['fstep']))
    return rec
full = ctx(X)
PTS = [(sl, v) for sl in (180, 200, 220) for v in (.35, .40, .45)]
sig_full = {p: S_lib.fam4(full, 3.0, p[1], 1.0, caution=('shock6m',), Lc=1.0, sl=p[0], band=0.02) for p in PTS}
rec_full = rec_v1(full, sig_full[(200, .40)])
res = {}
for cut in ('1995-06-30', '2001-03-30', '2008-10-31', '2012-07-31'):
    Xc = X.loc[:cut].copy(); cc = ctx(Xc); n = cc.r.shape[1]
    out = dict(days=int(n))
    out['flags_diff'] = int(sum(np.sum(cc.F[k] != full.F[k][:, :n]) for k in ('inv', 'shock6m')))
    out['signal_diff'] = int(sum(np.sum(S_lib.fam4(cc, 3.0, p[1], 1.0, caution=('shock6m',), Lc=1.0, sl=p[0], band=0.02) != sig_full[p][:, :n]) for p in PTS))
    rc = rec_v1(cc, sig_full[(200, .40)][:, :n]); m = rc.shape[0]
    out['engine_equity_maxabs'] = float(np.max(np.abs(rc[:, 0] - rec_full[:m, 0]))); out['engine_level_diff'] = int(np.sum(rc[:, 1] != rec_full[:m, 1]))
    res[cut] = out; print(cut, out, flush=True)
res['calendar_max'] = {bn: str(ix.max().date()) for bn, ix in L.dates().items()}
json.dump(res, open(OUT + 'v_lookahead.json', 'w'), indent=1)
