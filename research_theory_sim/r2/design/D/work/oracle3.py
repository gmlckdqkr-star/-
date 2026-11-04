import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
import exec_engine as ee, sim, rules
T = 7860; P = 1000
d = sim.simulate(P, T, 1, mechanism=True, states=True)
r, rf, y, p = d['r'], d['rf'], d['y10'], d['params']; close = np.cumprod(1 + r, axis=1)
k = rules.kfun(rf * 252); mb = p['mu_bar'][:, None]; sb = p['sigma_bar'][:, None]
S = y / 100 - rf * 252
carry = (p['phi'] * p['c'])[:, None] * (S - p['tpbar'][:, None])
cases = {'sig_t only': (mb + k) / p['_sig'] ** 2, 'mu_t only': (p['_mu'] + k) / sb ** 2,
         'carry only': (mb + carry + k) / sb ** 2, 'mu_t - carry': (p['_mu'] - carry + k) / sb ** 2}
for nm, D in cases.items():
    s = ee.summary(ee.run(r, rf, rules.track(np.clip(1.0 * D, 0, 3), close, rf, 0.25)))
    print('partial oracle f=1 %-14s %.4f lev %.2f tr %.1f' % (nm, s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']), flush=True)
