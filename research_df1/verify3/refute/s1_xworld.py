import os, sys, numpy as np, pandas as pd, json
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
END = pd.Timestamp('2014-12-31'); BLK=250
a, b, P, blk, seed = iv.POOLS['dev250']; print('pool', a, b, P, blk, seed)
R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
print('cols', list(X.columns), X.index.min().date(), X.index.max().date(), len(X))
lv = np.cumprod(1 + X['r'].fillna(0).values); D = X.index; n = len(X)
def pos(d): return int(D.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
excl = np.zeros(n, bool)
for p_, t_ in ((pk1,tr1),(pk2,tr2),(pk3,tr3)):
    e = min(t_ + BLK, n - 1); excl[p_:e + 1] = True
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
print('starts', len(starts))
# day coverage weight by block draws (uniform over allowed starts)
cov = np.zeros(n)
for s in starts: cov[s:s+BLK] += 1
cov /= cov.sum()
r = X['r'].fillna(0).values
rf = X['rf'].fillna(0).values if 'rf' in X else None
# bond: use the market dict from dfctx for rb (built from ctx); here use X columns if present
for c in X.columns: pass
yrs = pd.Series(D.year, index=D)
# share of sampled days by segment / by year
seg_id = np.full(n, -1); k = -1; prev = True
for i in range(n):
    if not excl[i]:
        if prev: k += 1
        seg_id[i] = k; prev = False
    else: prev = True
for s in range(k+1): print('segment', s, D[seg_id==s][0].date(), D[seg_id==s][-1].date(), 'days', (seg_id==s).sum(), 'sample weight %.3f' % cov[seg_id==s].sum())
# weighted mean daily return & vol of NDX in X world vs full world (unweighted full calendar for dev250 = uniform starts over all)
covF = np.zeros(n); startsF = np.arange(1, n-BLK)
for s in startsF: covF[s:s+BLK] += 1
covF /= covF.sum()
def wstats(w):
    m = (w*r).sum(); v = (w*(r-m)**2).sum(); return m*252, np.sqrt(v*252)
print('NDX ann mean, vol  X world: %.3f %.3f   full: %.3f %.3f' % (*wstats(cov), *wstats(covF)))
# 20d realized vol: share of sampled days with vol20 > 30%, and mean 20d-forward return when vol20>30%
v20 = pd.Series(r).rolling(20).std().values*np.sqrt(252)
hv = v20 > 0.30
print('share of sampled days with vol20>30%%: X %.3f  full %.3f' % ((cov*hv).sum(), (covF*hv).sum()))
fwd = pd.Series(np.log1p(r)[::-1]).rolling(60).sum().values[::-1]  # next-60d log return from day i
fwd = np.r_[fwd[1:], np.nan]
ok = ~np.isnan(fwd)
for nm, w in (('X', cov), ('full', covF)):
    w2 = w*hv*ok; print(nm, 'mean next-60d log return on high-vol days %.4f ; on low-vol days %.4f' % ((w2*np.nan_to_num(fwd)).sum()/w2.sum(), (w*(~hv)*ok*np.nan_to_num(fwd)).sum()/(w*(~hv)*ok).sum()))
np.save('/tmp/vf_refute/excl.npy', excl); np.save('/tmp/vf_refute/cov.npy', cov); np.save('/tmp/vf_refute/covF.npy', covF)
