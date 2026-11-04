import sys, numpy as np
from lib import *
P = 500; seeds = [11, 12]
for seed in seeds:
    for mech in (True, False):
        s, close = world(P, seed, mech)
        print(seed, 'ON' if mech else 'OFF', baselines(s))
x_all = {}
for k in (0.5, 1.0, 1.5):
    res = {}
    for seed in seeds:
        for mech in (True, False):
            s, close = world(P, seed, mech)
            x = np.diff(np.log(close), axis=1, prepend=np.log(close[:, :1]))
            sv = ewm(1.25 * np.sqrt(252) * np.abs(x), 250, init=np.full(P, 0.17))
            B = np.clip(k * 0.03 / sv ** 2, 0, 3)
            res['%d_%s' % (seed, 'ON' if mech else 'OFF')] = score(B, s)['cagr_med']
    n = log_variant('volscale', dict(k=k, hs=250, mu0=0.03), seeds, P, res)
    print(n, k, res)
