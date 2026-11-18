import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D, df5lib as L, df5data as DD
tr = D.trend_by_date()['tr']; ex = D.trend_by_date()['ex']
X1, S1 = L._src('1984-01-03', '2014-12-31', 'NDX')
a, b, P, blk, seed = L.iv.POOLS['dev250']; X2, S2 = L._src(a, b, 'NDX')
print('pool', a, b, P, blk)
for nm, S in (('REAL', S1), ('POOL', S2)):
    r = tr.reindex(S.index); print(nm, S.index.min().date(), S.index.max().date(), len(S), 'nan', int(r.isna().sum()), 'extra-days-not-in-trend', int((~S.index.isin(tr.index)).sum()))
print('corr ex DEVX-USD', ex[['DEVX','USD','SPX','GOLD','LTT']][ex.index>='1991-07-01'].corr().round(2).to_dict())
