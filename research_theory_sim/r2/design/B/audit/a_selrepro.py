# reproduce selection-seed variant records with the CURRENT sim.py (checks sim unchanged since selection; prior_scale=1 path)
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B/work'); import fam
T = 7860
for seed, mech, ref in ((21, True, 0.03971), (21, False, 0.04168)):
    s = sim.simulate(500, T, seed, mech); close = np.exp(np.cumsum(np.log1p(s['r']), axis=1)) * 100.0
    F = fam.feats(close, s['rf'])
    c = ee.summary(ee.run(s['r'], s['rf'], fam.level(F, k=0.6, hfwd=20, bh=0.1, hy=1)))['cagr_med']
    cr = ee.summary(ee.run(s['r'], s['rf'], rule.target_levels(close, s['rf'])))['cagr_med']
    print('N62 seed %d %s: fam %.5f (logged %.5f)  rule.py %.5f' % (seed, mech, c, ref, cr))
# N=1 volscale k=.5 seed 11 ON (logged 0.03343657910423925), uses lib-style close and ewm init 0.17
s = sim.simulate(500, T, 11, True); close = np.exp(np.cumsum(np.log1p(s['r']), axis=1)) * 100.0
x = np.diff(np.log(close), axis=1, prepend=np.log(close[:, :1]))
lam = 1 - 0.5 ** (1 / 250); sv = np.empty_like(x); v = np.full(500, 0.17)
for t in range(x.shape[1]): v = v + lam * (1.25 * np.sqrt(252) * np.abs(x[:, t]) - v); sv[:, t] = v
print('N1 seed 11 ON: %.17f (logged 0.03343657910423925)' % ee.summary(ee.run(s['r'], s['rf'], np.clip(0.5 * 0.03 / sv ** 2, 0, 3)))['cagr_med'])
