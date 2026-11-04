import numpy as np, pandas as pd, sys
from scipy.stats import spearmanr
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks, dsl
W2 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m2/'
z = np.load(W2+'m2data.npz'); cols = list(z['cols']); D = z['dec']; elig = z['elig']; SR = z['SR']
P = stocks.load(); idx = P.idx; PP = P.P
assert idx[-1] <= pd.Timestamp('2014-12-31')
Dall = np.flatnonzero(dsl.reb_rows(idx, 'monthly'))
s = cols.index('Mom12m')
res = {}
for Yoff in (0, 1, 2, 3):          # OAP yyyymm = M - Yoff ; Mom12m(Y) = P(end Y-1)/P(end Y-12) - 1
    cs = []
    for j in range(200, len(D), 3):
        jj = np.searchsorted(Dall, D[j])           # Dall[jj] = first row of month M
        e1 = jj - Yoff                             # first row of month Y ; end of Y-1 = Dall[e1]-1
        e0 = jj - Yoff - 11
        if e0 < 1 or e1 > len(Dall): continue
        b = (Dall[e1] - 1) if e1 < len(Dall) else D[j]
        a = Dall[e0] - 1
        mom = PP[b] / PP[a] - 1
        x = SR[j, :, s]; ok = np.isfinite(x) & np.isfinite(mom) & elig[j] & (a >= P.wfloor)
        if ok.sum() > 50: cs.append(spearmanr(x[ok], mom[ok]).correlation)
    res[Yoff] = (np.median(cs), len(cs))
    print('OAP Mom12m vs panel momentum assuming yyyymm = M-%d : median rank corr %.3f (n=%d)' % (Yoff, *res[Yoff]), flush=True)
