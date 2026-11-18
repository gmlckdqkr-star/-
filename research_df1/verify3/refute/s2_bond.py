import os, sys, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC
from dfctx import std
jp, iv = std.jp, std.iv
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
assert X.index.max() <= pd.Timestamp('2014-12-31')
excl = np.load('excl.npy'); cov = np.load('cov.npy'); covF = np.load('covF.npy')
rb = X['rb'].values.astype(float); rf = X['rf'].values.astype(float); r = X['r'].fillna(0).values
ok = ~np.isnan(rb) & ~np.isnan(rf)
ex = rb - rf
EX = 1.3988294390226633e-4
print('nan rb', np.isnan(rb).sum(), 'nan rf', np.isnan(rf).sum())
print('EX (df3) %.4e = %.2f%%/yr' % (EX, EX*252*100))
print('calendar mean (rb-rf) all days from idx1: %.4e' % np.nanmean(ex[1:]))
print('kept days unweighted mean: %.4e (%.2f%%/yr)' % (np.nanmean(ex[~excl]), np.nanmean(ex[~excl])*252*100))
print('excluded days mean: %.4e (%.2f%%/yr)' % (np.nanmean(ex[excl]), np.nanmean(ex[excl])*252*100))
w = cov*ok; print('X-world sampling-weighted mean: %.4e (%.2f%%/yr)' % ((w*np.nan_to_num(ex)).sum()/w.sum(), (w*np.nan_to_num(ex)).sum()/w.sum()*252*100))
w = covF*ok; print('full-world sampling-weighted mean: %.4e (%.2f%%/yr)' % ((w*np.nan_to_num(ex)).sum()/w.sum(), (w*np.nan_to_num(ex)).sum()/w.sum()*252*100))
# corr of bond and stock in kept vs excluded
for nm, m in (('kept', ~excl & ok), ('excl', excl & ok)): print(nm, 'corr(r, rb) %.3f' % np.corrcoef(r[m], rb[m])[0,1])
# refine high-vol forward-return stat: X world, forward window inside the same kept segment
seg = np.cumsum(np.r_[1, np.diff((~excl).astype(int)) != 0]) * (~excl)
v20 = pd.Series(r).rolling(20).std().values*np.sqrt(252); hv = v20 > 0.30
lr = np.log1p(r); cs = np.r_[0, np.cumsum(lr)]
n = len(r); f60 = np.full(n, np.nan); sameseg = np.zeros(n, bool)
for i in range(n-61):
    f60[i] = cs[i+61] - cs[i+1]; sameseg[i] = (seg[i] > 0) and (seg[i+60] == seg[i]) and not excl[i:i+61].any()
for nm, w, msk in (('X(same seg)', cov, sameseg), ('full', covF, ~np.isnan(f60))):
    h = w*hv*msk; l = w*(~hv)*msk
    print(nm, 'next-60d log ret | vol20>30%%: %.4f  vol20<=30%%: %.4f  share hv %.3f' % ((h*np.nan_to_num(f60)).sum()/h.sum(), (l*np.nan_to_num(f60)).sum()/l.sum(), h.sum()/(h.sum()+l.sum())))
# where do the X world's high-vol days sit?
yrs = X.index.year.values
hvx = hv & ~excl
print('X-world high-vol days by year:', {int(y): int(c) for y, c in zip(*np.unique(yrs[hvx], return_counts=True))})
