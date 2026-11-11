"""TW1 independent rough check (outside the engine's tax code): take the engine's pre-tax v1 curve (tax 0, same trades), apply a crude yearly tax on each
252-day block's gain (rate t, no deduction, no loss carry), and compare the CAGR gap 22% -> 11% with the engine's gap. Crude model taxes unrealized gains too,
so its level is lower; only sign and rough size of the GAP are compared. Also prints the tax-0 diagnostic (not a candidate row)."""
import os, sys
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/tw1/code')
import tw, ii
def crude(E, t):
    T = E.shape[1]; n = (T - 1) // 252; out = np.zeros(E.shape[0])
    for p in range(E.shape[0]):
        w = 1.0
        for y in range(n):
            r = E[p, (y + 1) * 252] / E[p, y * 252] - 1; w *= 1 + r - t * max(r, 0.0)
        r = E[p, T - 1] / E[p, n * 252] - 1; w *= 1 + r - t * max(r, 0.0)
        out[p] = w ** (252.0 / (T - 1)) - 1
    return out
for bn in tw.BASES:
    f0, E0 = tw.run(bn, 0.0, 0.003, 0.0); r0 = ii.stats(bn, f0, E0)
    f22, E22 = tw.run(bn, 0.22, 0.003, 0.0); f11, E11 = tw.run(bn, 0.11, 0.003, 0.0)
    r11 = ii.stats(bn, f11, E11)
    c22 = crude(E0, 0.22); c11 = crude(E0, 0.11)
    print('%-16s engine: tax0 d %+.4f | 11%% d %+.4f || crude gap 22->11: median %+.4f (crude levels 22%% %.4f, 11%% %.4f, pre-tax %.4f)' % (
        bn, r0['d'], r11['d'], float(np.median(c11 - c22)), float(np.median(c22)), float(np.median(c11)), float(np.median(crude(E0, 0.0)))), flush=True)
