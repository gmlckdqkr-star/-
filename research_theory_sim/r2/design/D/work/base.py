import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import exec_engine as ee, sim
T = 7860; P = int(sys.argv[1]) if len(sys.argv) > 1 else 600; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for mech in (True, False):
    d = sim.simulate(P, T, seed, mechanism=mech)
    r, rf = d['r'], d['rf']
    t0 = time.time()
    out = {}
    for lev in (1, 2, 3):
        out['hold%d' % lev] = ee.summary(ee.hold(r, rf, lev))['cagr_med']
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        s = ee.summary(ee.run(r, rf, np.full(r.shape, L)))
        out['const%.1f' % L] = s['cagr_med']
    print('mech', mech, 'seed', seed, 'P', P, ' '.join('%s=%.4f' % kv for kv in out.items()), ' (%.1fs)' % (time.time() - t0))
