import os, sys, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std'); os.environ.setdefault('NUMBA_NUM_THREADS','2')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC, dfe
from dfctx import std
for bn in ('real_ndx_86_14',):
    m = DC.market(bn); c = m['ctx']
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    print(bn, 'E', E.shape, 'ii', c.ii.shape, 'cagr', cg)
    idx = m['X_index']; off = c.ii.shape[1] - E.shape[1]
    e = E[0]; pk = np.maximum.accumulate(e); dd = e / pk - 1; t = int(np.argmin(dd)); p = int(np.argmax(e[:t + 1]))
    di = lambda j: idx[c.ii[0, j + off]].date()
    print('v1 MDD %.3f peak %s trough %s' % (dd[t], di(p), di(t)))
    # list drawdown episodes deeper than -40%
    i = 0; n = len(e); eps = []
    while i < n:
        if dd[i] < -0.4:
            j = i
            while j < n and dd[j] < 0: j += 1
            k = i + int(np.argmin(dd[i:j])); pp = int(np.argmax(e[:k + 1])); eps.append((di(pp), di(k), round(float(dd[k]), 3))); i = j
        else: i += 1
    print('v1 episodes < -40%:', eps)
    # TQQQ hold on same path, for comparison
    o, EE = dfe.run(m, np.full(m['r'].shape, 3.0), recon=True); e3 = EE[0]; dd3 = e3 / np.maximum.accumulate(e3) - 1
    print('TQQQ hold MDD %.3f' % dd3.min())
