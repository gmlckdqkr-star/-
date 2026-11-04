import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import exec_engine as ee, sim
T = 7860; P = 600
def kfun(rf):
    R = rf * 252
    return R / 3 - 0.0245 / 3 - 0.282 * np.maximum(R - 0.02, 0)
for mech in (True, False):
    d = sim.simulate(P, T, 1, mechanism=mech, states=True)
    r, rf, p = d['r'], d['rf'], d['params']
    k = kfun(rf)
    for f in (1.25, 1.5, 2.0):
        Bo = np.clip(f * (p['_mu'] + k) / p['_sig'] ** 2, 0, 3)
        Bs = np.clip(f * (p['mu_bar'][:, None] + k) / p['sigma_bar'][:, None] ** 2, 0, 3)
        so = ee.summary(ee.run(r, rf, Bo)); ss = ee.summary(ee.run(r, rf, Bs))
        print('mech', mech, 'f', f, 'oracle(mu_t,sig_t) med %.4f lev %.2f tr/y %.1f | static(mu_bar,sig_bar) med %.4f lev %.2f' % (
            so['cagr_med'], so['avg_level_med'], so['trades_per_year_med'], ss['cagr_med'], ss['avg_level_med']))
