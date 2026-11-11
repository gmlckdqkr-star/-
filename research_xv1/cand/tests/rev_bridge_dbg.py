import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand'); sys.path.insert(0, '/home/user/-/research_xv1/cand/tests')
import numpy as np, xv1, bridge, cbase as cm
import rev_bridge_xcheck as rx
for seed in (6, 10):
    sv, sB = rx.synth(seed)
    xv1.ref = lambda vv, _b=sB: dict(B=_b.copy(), bfn=None, bp=np.zeros(1), fstep=0.5)
    W = bridge.fast_crash(sv, X='LOSER', d=0.2, w=0.2)['Wt']; M = rx.my_fast(sv, sB, 'LOSER', 0.2)
    rows = np.flatnonzero((np.abs(W - M) > 1e-12).any(axis=1))
    print('seed', seed, 'rows', rows[:3], rows[-3:], 'cand cols', np.flatnonzero(W[rows[0]]), 'mine cols', np.flatnonzero(M[rows[0]]))
    t = int(rows[0])
    # first signal row of the differing stretch
    while t > 0 and (W[t - 1] != 0).any() and (M[t - 1] != 0).any(): t -= 1
    print(' stretch starts', t)
    for i, (k, f, p) in enumerate(rx.SECT):
        r1 = rx.one_x(sv, k, p); first = int(np.flatnonzero(~np.isnan(r1))[0]); win = r1[t - 62:t + 1]
        print('  ', k, 'first valid 1x row', first, 'rows of history at t', t - first + 1, 'NaN in window', int(np.isnan(win).sum()), 'rank of 63d return among valid', )
