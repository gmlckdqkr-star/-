"""E4 diagnosis (post-hoc): why frictionless vol targeting loses to constant leverage in X30.
(1) path-vol vs 'continuous' source-calendar vol (removes the block-junction staleness) (2) timing P&L by source year."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np, pandas as pd
import df5lib as L
WARM = 300; DQ = 0.0055
def perf(dr):
    lw = np.cumsum(np.log1p(dr), axis=1); lw = np.c_[np.zeros(dr.shape[0]), lw]
    cg = np.exp(lw[:, -1] / (dr.shape[1] / 252.0)) - 1; mdd = np.expm1((lw - np.maximum.accumulate(lw, axis=1)).min(axis=1)); return cg, mdd
def rstd(a, n):
    s = pd.Series(a).rolling(n).std().values; return s
for wname in ('X',):
    w = L.world(wname); m = w['m']; ii = w['ii']; Xs = w['X']
    rs = np.nan_to_num(Xs['r'].values.astype(float)); r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf'])
    print('m.r == src.r[ii]:', np.allclose(r[:, 1:], rs[ii][:, 1:]), 'src max date', Xs.index.max().date())
    T = r.shape[1]; sl = slice(WARM + 1, T); u = r + DQ / 252
    qcg, qmd = perf(u[:, sl]); q10 = np.percentile(qmd, 10)
    for wn in (20, 60):
        sd_src = rstd(rs, wn) * np.sqrt(252)
        sd_path = L.roll_std(r, wn) * np.sqrt(252)
        sd_cont = sd_src[ii]
        for s, lm in ((0.20, 1.0), (0.30, 1.0), (0.25, 1.5)):
            out = []
            for nm, sd in (('path', sd_path), ('cont', sd_cont)):
                Lt = np.where(np.isnan(sd), 0.0, np.minimum(lm, s / np.maximum(sd, 1e-9))); Lp = Lt[:, WARM:T - 1]
                cg, md = perf(Lp * u[:, sl] + (1 - Lp) * rf[:, sl])
                Lbar = Lp.mean()
                cgc, mdc = perf(Lbar * u[:, sl] + (1 - Lbar) * rf[:, sl])
                out.append('%s: med %.2f%% pair %+.2fpp ddm %+.1f%% | const L=%.2f med %.2f%% ddm %+.1f%%' % (nm, np.median(cg) * 100, np.median(cg - qcg) * 100,
                           (1 - abs(np.percentile(md, 10)) / abs(q10)) * 100, Lbar, np.median(cgc) * 100, (1 - abs(np.percentile(mdc, 10)) / abs(q10)) * 100))
            print('w%d s%.2f L%.1f || %s || %s' % (wn, s, lm, out[0], out[1]), flush=True)
    # timing P&L by source year, VT s0.20 w20 L1.0 with path vol
    sd = L.roll_std(r, 20) * np.sqrt(252); Lt = np.where(np.isnan(sd), 0.0, np.minimum(1.0, 0.2 / np.maximum(sd, 1e-9))); Lp = Lt[:, WARM:T - 1]
    ex = (u - rf)[:, sl]; tp = (Lp - Lp.mean()) * ex
    yrs = Xs.index.year.values[ii[:, sl]]
    df = pd.DataFrame({'y': yrs.ravel(), 'tp': tp.ravel(), 'ex': ex.ravel(), 'L': Lp.ravel()})
    g = df.groupby('y').agg(share=('tp', 'size'), timing_pnl=('tp', 'sum'), mean_ex=('ex', 'mean'), meanL=('L', 'mean'))
    g['share'] = g['share'] / len(df); g['timing_pnl'] = g['timing_pnl'] / tp.shape[0] / 30   # per path-year contribution to annual arithmetic return
    g['mean_ex'] = g['mean_ex'] * 252
    print('total timing pnl (arith, per yr) %.4f' % (tp.sum() / tp.shape[0] / 30))
    print(g.round(4).to_string())
    # vol -> next-20d return relation in X sample
    nx = pd.DataFrame(ex).T.rolling(20).sum().shift(-20).T.values if False else None
