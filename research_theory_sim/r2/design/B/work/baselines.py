"""baselines on selection seeds: holds and constant levels (no rule). Descriptive."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim
T = 7860; P = int(sys.argv[1]) if len(sys.argv) > 1 else 1000; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for mech in (True, False):
    s = sim.simulate(P, T, seed, mech)
    r, rf = s['r'], s['rf']
    out = {}
    for lev in (1, 2, 3):
        out['hold%d' % lev] = ee.summary(ee.hold(r, rf, lev))['cagr_med']
    for L in np.arange(0.5, 3.01, 0.5):
        out['const%.1f' % L] = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']
    print('ON ' if mech else 'OFF', ' '.join('%s=%.4f' % kv for kv in out.items()))
