import numpy as np, pandas as pd, sys
from scipy.stats import spearmanr
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks, dsl
W2 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m2/'
z = np.load(W2+'m2data.npz'); D = z['dec']; elig = z['elig']; HR = z['HR']; dd = pd.to_datetime(z['ddate'].astype('datetime64[D]'))
P = stocks.load(); PP = P.P; idx = P.idx; Dall = np.flatnonzero(dsl.reb_rows(idx, 'monthly'))
def ic_of(sigfun, a='1986-01-01', b='1999-12-31'):
    out = []
    for j in np.flatnonzero((dd >= a) & (dd <= b)):
        x = sigfun(j); ok = np.isfinite(x) & elig[j]
        if ok.sum() > 50: out.append(spearmanr(x[ok], HR[j, ok]).correlation)
    out = np.array(out); return out.mean(), out.mean()/out.std(ddof=1)*np.sqrt(len(out))
def rev(lagm):
    def f(j):
        jj = np.searchsorted(Dall, D[j]); a, b = Dall[jj-lagm] - 1, Dall[jj-lagm+1] - 1
        return -(PP[b]/PP[a] - 1) if a >= 0 else np.full(PP.shape[1], np.nan)
    return f
def mom(lagm):
    def f(j):
        jj = np.searchsorted(Dall, D[j]); b = Dall[jj-lagm] - 1; a = Dall[jj-lagm-11] - 1
        x = PP[b]/PP[a] - 1; x[a < P.wfloor] = np.nan; return x
    return f
for nm, f in (('STrev month M-1 (standard)', rev(1)), ('STrev month M-2 (worker)', rev(2)),
              ('Mom 12-1 end M-2 (standard 12-1)', mom(1)), ('Mom end M-3 (worker OAP M-2)', mom(2))):
    for per in (('1986-01-01', '1999-12-31'), ('2000-01-01', '2014-12-31')):
        m, t = ic_of(f, *per); print('%-34s %s..%s IC %.4f t %.2f' % (nm, per[0][:4], per[1][:4], m, t), flush=True)
