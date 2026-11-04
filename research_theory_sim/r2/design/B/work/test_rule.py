import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B')
import rule
from lib import *
import fam
s, close = world(300, 21, True)
F = fam.feats(close, s['rf'])
L1 = fam.level(F, k=0.6, hfwd=20, bh=0.1, hy=1)
c0 = close.copy(); f0 = s['rf'].copy()
L2 = rule.target_levels(close, s['rf'])
assert np.array_equal(c0, close) and np.array_equal(f0, s['rf']), 'inputs modified'
d = np.nanmax(np.abs(L1[:, 300:] - L2[:, 300:])); print('max diff fam vs rule (traded cols):', d)
print('scores fam', score(L1, s)['cagr_med'], 'rule', score(L2, s)['cagr_med'])
# scale invariance
L3 = rule.target_levels(close * 1234.5, s['rf']); print('scale-invariant:', np.allclose(np.nan_to_num(L2, nan=-1), np.nan_to_num(L3, nan=-1)))
# causality: changing future columns must not change past outputs
c2 = close.copy(); c2[:, 5000:] *= np.exp(np.random.default_rng(0).normal(0, 0.05, (300, close.shape[1] - 5000)))
L4 = rule.target_levels(c2, s['rf']); print('causal:', np.array_equal(np.nan_to_num(L2[:, :5000], nan=-1), np.nan_to_num(L4[:, :5000], nan=-1)))
# NaN prefix, zeros, flat stretch
c3 = close[:5].copy(); c3[0, :800] = np.nan; c3[1, :500] = 0.0; c3[2, 1000:1600] = c3[2, 1000]; c3[3, 2000:2010] = np.nan
r3 = s['rf'][:5].copy(); r3[4, :100] = np.nan
L5 = rule.target_levels(c3, r3)
print('nan-handling: finite in [0,3]:', np.all((L5[np.isfinite(L5)] >= 0) & (L5[np.isfinite(L5)] <= 3)), 'first valid col per path', [int(np.argmax(np.isfinite(L5[i]))) for i in range(5)])
print('flat stretch levels path2 999/1300/1599:', L5[2, 999], L5[2, 1300], L5[2, 1599])
# 1-D input
print('1-D ok', rule.target_levels(close[0], s['rf'][0]).shape)
# speed
g = np.random.default_rng(1); cc = 100 * np.exp(np.cumsum(g.normal(0.0003, 0.011, (500, 10000)), axis=1)); ff = np.full((500, 10000), 0.03 / 252)
t0 = time.time(); rule.target_levels(cc, ff); print('speed P=500 T=10000: %.2fs' % (time.time() - t0))
