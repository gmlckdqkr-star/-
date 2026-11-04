"""equivalence of rule.py with the design implementation, speed, causality, scale invariance, NaN handling."""
import sys, time
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A/work')
import numpy as np, sim, rule
from clock import clock_rule
from harness import close_of
w = sim.simulate(200, 7860, 7, mechanism=True)
cl = close_of(w['r'])
B1 = rule.target_levels(cl, w['rf'])
B2 = clock_rule(cl, p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
d = np.abs(np.nan_to_num(B1, nan=-1) - B2)
print('max diff vs design impl (cols>=1):', d[:, 1:].max(), ' col0', B1[:, 0][:3], B2[:, 0][:3])
# scale invariance
B3 = rule.target_levels(cl * 1234.5, w['rf']); print('scale invariance max diff', np.nanmax(np.abs(B3 - B1)))
# causality: perturb future
cl2 = cl.copy(); cl2[:, 5000:] *= np.exp(np.random.default_rng(0).normal(0, 0.05, (200, 2860))).cumprod(axis=1)
B4 = rule.target_levels(cl2, w['rf']); print('causal (cols<5000 equal):', np.array_equal(np.nan_to_num(B4[:, :5000], nan=-9), np.nan_to_num(B1[:, :5000], nan=-9)))
# input not modified
c0 = cl.copy(); _ = rule.target_levels(cl, w['rf']); print('input unchanged', np.array_equal(c0, cl))
# NaN / zero / flat leading stretch
cl3 = cl.copy(); cl3[:, :400] = np.nan; cl3[:3, 400:600] = cl3[:3, 600:601]; cl3[5, 1000:1010] = 0.0; cl3[6, 2000:2100] = cl3[6, 1999:2000]
B5 = rule.target_levels(cl3, w['rf']); print('nan/flat ok: range', np.nanmin(B5), np.nanmax(B5), 'nan cols lead', np.isnan(B5[:, :400]).all(), 'finite after', np.isfinite(B5[:, 700:]).all())
# 1-D input
print('1d ok', rule.target_levels(cl[0], w['rf'][0]).shape)
# speed P=500, T=10000
g = np.random.default_rng(1); r = g.normal(0.0003, 0.011, (500, 10000)); r[:, 0] = 0
t0 = time.time(); _ = rule.target_levels(np.cumprod(1 + r, axis=1), np.full((500, 10000), 1e-4)); print('speed P=500 T=10000: %.1fs' % (time.time() - t0))
