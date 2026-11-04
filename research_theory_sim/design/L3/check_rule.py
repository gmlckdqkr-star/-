"""Checks of rule.py: speed, causality, scale invariance, NaN handling, agreement with the design implementation."""
import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L3')
import rule, design_lib as dl, rules_lib as rl, sim
g = np.random.default_rng(123)
P, T = 500, 10000
r = g.normal(0.0003, 0.011, (P, T)); r[:, 0] = 0
close = np.cumprod(1 + r, axis=1) * 37.0; rf = np.full((P, T), 0.02 / 252)
t0 = time.time(); B = rule.target_levels(close, rf); dt = time.time() - t0
print(f'speed P=500 T=10000: {dt:.1f}s', B.shape, B.dtype)
# causality: change the future after column k, earlier columns must be identical
k = 5000; c2 = close.copy(); c2[:, k + 1:] *= np.exp(g.normal(0, 0.05, (P, T - k - 1))).cumprod(1); rf2 = rf.copy(); rf2[:, k + 1:] = 0.1 / 252
B2 = rule.target_levels(c2, rf2)
print('causal:', np.array_equal(np.nan_to_num(B[:, :k + 1], nan=-9), np.nan_to_num(B2[:, :k + 1], nan=-9)))
# scale invariance
B3 = rule.target_levels(close * 1234.5, rf)
print('scale-invariant (max abs diff):', np.nanmax(np.abs(B3 - B)))
# NaN handling: leading NaNs, gaps, NaN rf
c4 = close.copy(); c4[:50, :400] = np.nan; c4[:, 7000:7010] = np.nan; rf4 = rf.copy(); rf4[:, 100:200] = np.nan
B4 = rule.target_levels(c4, rf4)
print('NaN case: finite share', np.isfinite(B4).mean().round(4), 'range', np.nanmin(B4), np.nanmax(B4), 'first finite col path0', np.argmax(np.isfinite(B4[0])))
# 1-D input
print('1-D input shape', rule.target_levels(close[0], rf[0]).shape)
# agreement with the design implementation on synthetic SGNC data (design seed 1, first 300 paths)
rr, ff = dl.get(1, True, 2000); rr, ff = rr[:300], ff[:300]
C = dl.close_from(rr)
Bd = rl.fam_kz(C, ff, a=0.005, beta=0.01, N=126, Hv=60, Hz=60)
Br = rule.target_levels(C, ff)
m = np.arange(Br.shape[1]) >= 300
print('max |rule - design| after warm-up:', np.nanmax(np.abs(Br[:, m] - Bd[:, m])))
sd = dl.evaluate(rr, ff, Bd)['cagr_med']; sr = dl.evaluate(rr, ff, Br)['cagr_med']
print('median CAGR design impl %.5f  rule.py %.5f' % (sd, sr))
