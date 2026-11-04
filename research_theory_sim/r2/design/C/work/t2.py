import sys, time; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/C')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import numpy as np, sim, exec_engine as ee
T = 7860
s = sim.simulate(250, T, 1, mechanism=True, diag=True)
m = s['diag']['m']; vd = s['diag']['var_d']; lam = s['diag']['lam']
print('m/yr percentiles', np.percentile(m, [1, 5, 25, 50, 75, 95, 99]).round(3))
print('std of m per path median', np.median(m.std(1)).round(3))
p = s['params']
print('rf/yr pct', (np.percentile(s['rf'], [5, 25, 50, 75, 95]) * 252).round(4))
# oracle Kelly with true m and total var
EY2 = p['Ybar']**2*(1+1/p['kY'])
v = vd + lam * EY2[:, None]
for k in (0.5, 1.0):
    B = np.clip(k * m / v, 0, 3)
    res = ee.run(s['r'], s['rf'], B)
    print('oracle kelly frac', k, ee.summary(res)['cagr_med'], ee.summary(res)['avg_level_med'], ee.summary(res)['trades_per_year_med'])
# oracle var-only
for c in (0.03,):
    B = np.clip(c / v, 0, 3); res = ee.run(s['r'], s['rf'], B); print('oracle var-only c', c, ee.summary(res)['cagr_med'])
for L in (0.5, 1, 1.5, 2, 2.5, 3):
    print('const', L, round(ee.summary(ee.run(s['r'], s['rf'], np.full(s['r'].shape, float(L))))['cagr_med'], 4))
print('hold1', ee.summary(ee.hold(s['r'], s['rf'], 1))['cagr_med'])
