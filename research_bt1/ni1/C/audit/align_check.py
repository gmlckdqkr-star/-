"""Audit check: panel vs KF date alignment (lag 0 vs +-1) and month-to-month industry stability. No names read."""
import sys, io, lzma, numpy as np, pandas as pd
KFP, PAN = sys.argv[1:3]
L = open(KFP).read().splitlines()
i0 = next(i for i, l in enumerate(L) if 'Average Value Weighted Returns -- Daily' in l)
i1 = next(i for i, l in enumerate(L) if 'Average Equal Weighted Returns -- Daily' in l)
rec = {int(p[0]): [float(q) for q in p[1:]] for p in ([q.strip() for q in l.split(',')] for l in L[i0+2:i1]) if len(p) == 18 and p[0].isdigit()}
kf = pd.DataFrame.from_dict(rec, orient='index').sort_index() / 100
z = np.load(io.BytesIO(lzma.open(PAN).read()))
dt = pd.to_datetime(z['dates'], unit='D'); adj = z['adj'].astype(float); T = len(dt)
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
r = adj[1:] / adj[:-1] - 1; r[~(mem[1:] & mem[:-1])] = np.nan
ew = pd.Series(np.nanmean(r, 1), index=dt[1:].strftime('%Y%m%d').astype(int))
km = kf.mean(1).reindex(ew.index)
print('missing KF rows for panel dates <=2014:', int(km.isna().sum()))
for lag in (-1, 0, 1):
    print('lag', lag, 'corr EW panel vs mean KF VW:', round(ew.corr(km.shift(lag)), 4))
for a, b in ((19860101, 19991231), (20000101, 20141231)):
    s = (ew.index >= a) & (ew.index <= b)
    print(a, b, 'lag0 corr', round(ew[s].corr(km[s]), 4))
