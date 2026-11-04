import numpy as np, pandas as pd, sys
from scipy.stats import spearmanr
W2 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m2/'
z = np.load(W2+'m2data.npz')
cols = list(z['cols']); dd = pd.to_datetime(z['ddate'].astype('datetime64[D]')); D = z['dec']
HR = z['HR']; elig = z['elig']; SR = z['SR']; year = z['year']; sign = z['sign']
ic = np.load(W2+'ic_cache.npz')['ic']
print('decisions', dd[0].date(), dd[-1].date(), len(dd), 'signals', len(cols))
for nm in ('Mom12m', 'BM', 'AssetGrowth', 'STreversal', 'Accruals'):
    s = cols.index(nm)
    mine = np.full(len(dd), np.nan)
    for j in range(len(dd)):
        x = SR[j, :, s]; ok = np.isfinite(x) & elig[j]
        if ok.sum() >= 30: mine[j] = spearmanr(x[ok], HR[j, ok]).correlation
    disc = (dd.year >= 1986) & (dd.year <= 1999)
    m = disc & np.isfinite(mine) & np.isfinite(ic[:, s]) & (dd.year >= year[s] + 1)
    print('%-12s sign %+d pubyear %d  max|mine-worker| %.2e  disc usable-month mean IC mine %.4f worker %.4f (n=%d)' % (
        nm, sign[s], year[s], np.nanmax(np.abs(mine - ic[:, s])), mine[m].mean(), ic[m, s].mean(), m.sum()))
np.save('dd.npy', dd.values)
