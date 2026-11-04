import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import sim, exec_engine as ee
np.seterr(all='ignore')
P, T = 1000, 7860
for mech in (True, False):
    s = sim.simulate(P, T, seed=2, mechanism=mech)
    r, rf = s['r'], s['rf']
    out = {}
    t0 = time.time()
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        out[L] = ee.summary(ee.run(r, rf, np.full((P, T), L)))['cagr_med']
    print('mech', mech, 'engine time per run %.1fs' % ((time.time() - t0) / 6))
    print(' const', {k: round(v, 4) for k, v in out.items()})
    print(' hold', {L: round(ee.summary(ee.hold(r, rf, L))['cagr_med'], 4) for L in (1, 2)})
