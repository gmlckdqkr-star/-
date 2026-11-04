import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import rule, cands as c, harness as h, exec_engine as ee
np.seterr(all='ignore')
r, rf = h.data(11, True)
close = np.cumprod(1 + r, axis=1)
B1 = rule.target_levels(close, rf)
p = dict(rule.PARAMS, kf=0.5)
B2 = c.F_kelly(close, rf, p)
d = np.abs(B1[:, 300:] - B2[:, 300:])
print('max |rule - cands| after warmup', np.nanmax(d), 'mean', np.nanmean(d))
print('engine rule', round(ee.summary(ee.run(r, rf, B1))['cagr_med'], 4), 'cands', round(ee.summary(ee.run(r, rf, B2))['cagr_med'], 4))
# scale invariance
B3 = rule.target_levels(close * 1234.5, rf)
print('scale invariance max diff', np.nanmax(np.abs(B3 - B1)))
# causality: change future, past unchanged
cl2 = close.copy(); cl2[:, 5000:] *= np.exp(np.random.default_rng(0).normal(0, 0.05, (cl2.shape[0], cl2.shape[1] - 5000))).cumprod(1)
rf2 = rf.copy(); rf2[:, 5000:] = 0.2 / 252
B4 = rule.target_levels(cl2, rf2)
print('causality: max diff before t=5000', np.nanmax(np.abs(B4[:, :5000] - B1[:, :5000])))
# NaN handling
cl3 = close.copy(); cl3[:10, :50] = np.nan; cl3[:10, 1000:1010] = np.nan; rf3 = rf.copy(); rf3[:5, :100] = np.nan
B5 = rule.target_levels(cl3, rf3)
print('NaN: output finite share after warmup', np.isfinite(B5[:, 300:]).mean(), 'range', np.nanmin(B5), np.nanmax(B5))
# speed P=500, T=10000
g = np.random.default_rng(1); cl = np.exp(np.cumsum(g.normal(0.0003, 0.01, (500, 10000)), 1)); rr = np.full((500, 10000), 0.03 / 252)
t0 = time.time(); B6 = rule.target_levels(cl, rr); print('speed P=500 T=10000: %.1fs' % (time.time() - t0), B6.dtype, B6.shape)
# 1-D input
print('1-D ok', rule.target_levels(close[0], rf[0]).shape)
