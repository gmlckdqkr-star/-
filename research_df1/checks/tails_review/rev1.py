import sys, copy, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2, ov, jp, iv
sys.path.insert(1, '/tmp/rev_tails/tl'); import tails as TL
W = dfe.WARM
G = TL.G
PICKS = TL.PICKS; LIM = TL.LIM
m0 = DC.market('dev250_path'); c0 = m0['ctx']; X = TL.X_of('dev250_path'); P, T = c0.r.shape
print('pool', iv.POOLS['dev250'], 'P,T', P, T, 'X', X.index.min(), X.index.max())
# 1. no-gap reproduction
mN = TL.gap_market(c0, X, None, 0.0)
for k in ('r', 'rf', 'rb', 'cpn', 'idxup', 'bondup', 'st_v1', 'st_al', 'vol20'):
    a, b = np.asarray(m0[k], float), np.asarray(mN[k], float)
    print('nogap', k, 'equal' if np.array_equal(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9)) else 'DIFF maxabs %g' % np.nanmax(np.abs(a - b)))
for pk in PICKS:
    o0 = R2.run_cfg(dict(G[PICKS[pk]]['cfg']), m0); o1 = R2.run_cfg(dict(G[PICKS[pk]]['cfg']), mN)
    print('nogap engine', pk, float(np.max(np.abs(o0 - o1))))
# 2. independent gap ctx built from scratch (no shallow copy of c0), official engine
def fresh_gap(days, g):
    c = object.__new__(ov.Ctx)
    c.ii = c0.ii.copy(); c.r = c0.r.copy(); c.rf = c0.rf.copy(); c.rb = None if c0.rb is None else c0.rb.copy()
    c.vix = None if c0.vix is None else c0.vix.copy(); c.F = {k: v.copy() for k, v in c0.F.items() if k not in ('one', 'none')}
    c.P, c.T = c.r.shape; c._c = {}
    c.r[np.arange(P), days] = g; c.lvl = np.cumprod(1 + c.r, axis=1)
    return DC._finish(c, X)
days = np.random.default_rng(23).integers(W + 1, T, size=P)
res = {}
for g in (-0.20, -0.25):
    m = fresh_gap(days, g); mT = TL.gap_market(c0, X, days, g)
    print('gap', g, 'st_v1 equal to TL:', np.array_equal(m['st_v1'], mT['st_v1']), 'vol20 eq', np.allclose(np.nan_to_num(m['vol20']), np.nan_to_num(mT['vol20'])))
    # manual check of vol20 at the gap day for path 0
    p = 0; d = days[p]; lr = np.log1p(m['r'][p, d - 19:d + 1]); mv = np.sqrt(max(np.mean(lr * lr) - np.mean(lr) ** 2, 0) * 252)
    print('  path0 gap day', d, 'r', m['r'][p, d], 'vol20 manual %.4f engine %.4f base %.4f' % (mv, m['vol20'][p, d], m0['vol20'][p, d]),
          'st_v1 d..d+3', m['st_v1'][p, d:d + 4], 'base', m0['st_v1'][p, d:d + 4])
    for pk in PICKS:
        cg, md = dfe.stats(R2.run_cfg(dict(G[PICKS[pk]]['cfg']), m), T)
        wd = min(np.percentile(md, 10), G[PICKS[pk]]['real_ndx_86_14']['mdd'], G[PICKS[pk]]['real_spx_29_54']['mdd'])
        res['%s|g%d' % (pk, -g * 100)] = dict(cagr=float(np.median(cg)), p10=float(np.percentile(md, 10)), Pbr=float(np.mean(md < LIM[pk])), WD=float(wd))
        print('  %-11s cagr %.4f p10 %.4f P<lim %.3f WD %.4f' % (pk, np.median(cg), np.percentile(md, 10), np.mean(md < LIM[pk]), wd))
    del m, mT
# 3. how often the base bootstrap already contains a big crash day in the scoring window
rs = c0.r[:, W:]
mn = rs.min(axis=1)
print('per-path min daily r in scoring window: quantiles', np.percentile(mn, [0, 10, 25, 50, 75, 90, 100]).round(4))
print('share of paths with a day <= -0.10: %.3f, <= -0.14: %.3f' % (np.mean(mn <= -0.10), np.mean(mn <= -0.14)))
print('expected count of days <= -0.14 per path: %.3f' % np.mean((rs <= -0.14).sum(axis=1)))
json.dump(res, open('/tmp/rev_tails/rev1.json', 'w'), indent=1)
