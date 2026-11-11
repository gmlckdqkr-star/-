"""Reviewer: structure of the chip-series episodes (dates and row counts only): when an episode opens and ends, on how many
of its rows the depth condition holds, and on how many of those v1's target level is <= 1. No performance figure."""
import sys
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, bridge, cbase as cm
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(['semis', 'ret:SOXL'], X.index)); i0 = len(X) - v.T; dt = lambda t: str(X.index[i0 + t].date())
S = cm.level(v.x['semis']); H, high, dd = bridge._highs(S); L = v.ref_target; B = xv1.ref(v)['B']
print('high days of the chip series', int(high.sum()), 'in warm-up', int(high[:300].sum()))
for name, dep in (('A', bridge.D_SET['A']), ('B', bridge.D_SET['B'])):
    W = np.asarray(bridge.staged_bridge(v, depth_set=name, budget=0.3)['Wt'])[:, 0]
    phase = 0; op = None; eps = []
    for t in range(v.T):
        if high[t]:
            if op is not None: eps.append((op, t)); op = None
            phase = 1
        elif phase == 1 and dd[t] <= -dep[0]: phase = 2; op = t
    if op is not None: eps.append((op, v.T - 1))
    print('depth set', name, 'episodes', len(eps))
    for a, b in eps:
        r = np.arange(a, b + 1); c = [int(((dd[r] <= -d) & (L[r] <= 1)).sum()) for d in dep]; c0 = [int((dd[r] <= -d).sum()) for d in dep]
        print('   opens', dt(a), 'ends', dt(b), 'rows', len(r), 'rows at depth 1/2/3', c0, 'of these with L <= 1', c, 'rows with weight', int((W[r] != 0).sum()),
              'weight steps (thirds)', sorted(set(np.round(W[r] / 0.1).astype(int).tolist())))
