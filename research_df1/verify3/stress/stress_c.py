"""stress C: paired per-path W40 - T40 (same paths) in P, P0 and X seeds 7/8/9; cost 0 / 0.15% mechanism check; trade counts. <=2014 only."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
EX = 1.3988294390226633e-4; END = pd.Timestamp('2014-12-31'); BLK = 250; YRS = 30
OUTD = '/mnt/project-files/research/df1/verify3/stress/'
ALLC = {c['id']: c for c in RG.configs() + R2.configs()}
T40 = ALLC['v1|s0.3|L1.0|K2|RB']; W40 = ALLC['DF2|M0|b3|v1|s0.3|L1.0|K2|RB']
def run_any(cfg, m, **extra):
    return R2.run_cfg(cfg, m, **extra) if cfg.get('fam') == 'df2' else RG.run_cfg(cfg, m, **extra)
def paired(m, **extra):
    Tm = m['r'].shape[1]; ot = run_any(T40, m, **extra); ow = run_any(W40, m, **extra)
    ct, mt = dfe.stats(ot, Tm); cw, mw = dfe.stats(ow, Tm); dc = cw - ct; dm = mw - mt
    return dict(T40_cagr=float(np.median(ct)), W40_cagr=float(np.median(cw)), d_cagr_med=float(np.median(dc)), d_cagr_p10=float(np.percentile(dc, 10)),
                d_cagr_p90=float(np.percentile(dc, 90)), share_W_higher=float(np.mean(dc > 0)), d_mdd_med=float(np.median(dm)),
                d_mdd_p10=float(np.percentile(dm, 10)), share_W_mdd_deeper=float(np.mean(dm < 0)),
                T40_mddp10=float(np.percentile(mt, 10)), W40_mddp10=float(np.percentile(mw, 10)),
                ntr_T40=float(np.median(ot[:, 4])), ntr_W40=float(np.median(ow[:, 4])), costp_T40=float(np.median(ot[:, 6])), costp_W40=float(np.median(ow[:, 6])))
RES = {}
mp = DC.market('dev250_path'); assert mp['X_index'].max() <= END
mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX
RES['P'] = paired(mp); RES['P_cost0'] = paired(mp, cost=0.0); RES['P_cost0015'] = paired(mp, cost=0.0015); RES['P_cost2x'] = paired(mp, cost=0.006)
RES['P_delay3'] = paired(mp, delay=3); RES['P0'] = paired(mp0); RES['P0_cost2x'] = paired(mp0, cost=0.006)
DC._M.pop('dev250_path', None); del mp, mp0
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
lv = np.cumprod(1 + X['r'].fillna(0).values); D = X.index; n = len(X)
def pos(d): return int(D.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
excl = np.zeros(n, bool)
for p_, t_ in ((pk1, tr1), (pk2, tr2), (pk3, tr3)): e = min(t_ + BLK, n - 1); excl[p_:e + 1] = True
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
T = ov.WARM + YRS * 252; nb = T // BLK + 1; F = ov.flags_hist(X)
for SEED in (7, 8, 9):
    g = np.random.default_rng(SEED); st = starts[g.integers(0, len(starts), (P, nb))]
    iiX = (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T]; assert not excl[iiX].any()
    cX = ov.Ctx(X, F, iiX); cX.F = std.path_flags(X, iiX); cX._c = {}; mX = DC._finish(cX, X); mX0 = dict(mX); mX0['rb'] = mX['rb'] - EX
    RES['X_s%d' % SEED] = paired(mX); RES['X0_s%d' % SEED] = paired(mX0)
for k, v in RES.items():
    print('%-12s T40 %.4f W40 %.4f | dCAGR med %+.4f p10 %+.4f p90 %+.4f W>T %.2f | dMDD med %+.4f p10 %+.4f Wdeeper %.2f | mddp10 T %.4f W %.4f | ntr %.0f/%.0f cost %.3f/%.3f' % (
        k, v['T40_cagr'], v['W40_cagr'], v['d_cagr_med'], v['d_cagr_p10'], v['d_cagr_p90'], v['share_W_higher'], v['d_mdd_med'], v['d_mdd_p10'],
        v['share_W_mdd_deeper'], v['T40_mddp10'], v['W40_mddp10'], v['ntr_T40'], v['ntr_W40'], v['costp_T40'], v['costp_W40']))
json.dump(RES, open(OUTD + 'stress_c_paired.json', 'w'), indent=1)
