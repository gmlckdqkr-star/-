import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, exec_engine as ee
for seed in (11, 12):
    for mech in (True, False):
        r, rf = h.data(seed, mech)
        P = r.shape[0]
        c = {L: round(ee.summary(ee.run(r, rf, np.full((P, h.T), L)))['cagr_med'], 4) for L in (0.5, 1.0, 1.5, 2.0, 3.0)}
        hd = {L: round(ee.summary(ee.hold(r, rf, L))['cagr_med'], 4) for L in (1, 2, 3)}
        print('seed', seed, 'mech', mech, 'const', c, 'hold', hd)
