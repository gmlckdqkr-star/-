import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
import exec_engine as ee, sim, rules
T = 7860; P = 1000
for mech in (True, False):
    d = sim.simulate(P, T, 1, mechanism=mech, states=True)
    r, rf, p = d['r'], d['rf'], d['params']; close = np.cumprod(1 + r, axis=1)
    k = rules.kfun(rf * 252)
    print('mech', mech, 'hold1 %.4f' % ee.summary(ee.hold(r, rf, 1))['cagr_med'], flush=True)
    for f in (1.0, 1.5):
        Bo = np.clip(f * (p['_mu'] + k) / p['_sig'] ** 2, 0, 3)
        Bs = np.clip(f * (p['mu_bar'][:, None] + k) / p['sigma_bar'][:, None] ** 2, 0, 3)
        so = ee.summary(ee.run(r, rf, rules.track(Bo, close, rf, 0.25))); ss = ee.summary(ee.run(r, rf, rules.track(Bs, close, rf, 0.25)))
        print('  f', f, 'tracked oracle(mu_t,sig_t) %.4f | tracked static(mu_bar,sig_bar) %.4f' % (so['cagr_med'], ss['cagr_med']), flush=True)
