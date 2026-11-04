"""ceiling check (NOT a candidate rule): per-path constant level from the TRUE mu, sigma (uses simulator params)."""
import sys, numpy as np
from lib import *
P = 500; seeds = [11, 12]
for k in (0.5, 1.0):
    res = {}
    for seed in seeds:
        for mech in (True, False):
            s, close = world(P, seed, mech); pr = s['params']
            L = np.clip(k * pr['mu'] / pr['sigma'] ** 2, 0, 3)
            B = np.repeat(L[:, None], s['r'].shape[1], axis=1)
            res['%d_%s' % (seed, 'ON' if mech else 'OFF')] = score(B, s)['cagr_med']
    print('oracle-const k', k, res)
