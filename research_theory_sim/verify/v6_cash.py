"""TS1 verifier, sensitivity only (<=2014): MS1 cash = max(rf-2%,0)*0.846. How much would L1 / s0.85 gain with cspr=0?"""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa
sys.path.insert(0, '/mnt/project-files/research/theory_sim/verify'); from v2b_engine import load  # noqa
C = std.contexts(); rule = load('L1')
for bn in ('dev250_path', 'real_ndx_86_14'):
    c = C[bn]; B = np.asarray(rule.target_levels(np.array(c.lvl), np.array(c.rf)), dtype=np.float64)
    rB, rbf, rbp, rfs = std.s085(c)
    for cs in (0.02, 0.0):
        f, _ = std.engine(c, B, std.ident, np.zeros(1), 0.5, cspr=cs); g, _ = std.engine(c, rB, rbf, rbp, rfs, cspr=cs)
        print('%-15s cspr=%.2f  L1 %.4f  s0.85 %.4f  pw %.3f' % (bn, cs, np.median(f), np.median(g), np.mean(f - g > 1e-5)), flush=True)
