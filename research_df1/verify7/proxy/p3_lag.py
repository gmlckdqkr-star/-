"""verify7/proxy: where does the lag-1 vs lag-2 (and phase) difference come from? per market x period; lag-1 autocorrelation of each market's excess return. <=2014."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/verify7/proxy')
import p2_sens as P   # rebuilds base data (prints its own JSON; harmless)
OUT = '/tmp/df7v_proxy/proxy_lag.json'
ex = P.build_ex(); R = {}
w1, t1 = P.trend(ex, lag=1); w2, t2 = P.trend(ex, lag=2)
w1d, _ = P.trend(ex, lag=1, reb=1); w2d, _ = P.trend(ex, lag=2, reb=1)
E = ex.fillna(0.0)
pers = {'1986_1992': ('1986-01-01', '1992-12-31'), '1993_1999': ('1993-01-01', '1999-12-31'), '2000_2007': ('2000-01-01', '2007-12-31'), '2008_2014': ('2008-01-01', '2014-12-31'), '1986_2014': ('1986-01-01', '2014-12-31')}
for nm, (a, b) in (('weekly', (w1, w2)), ('daily', (w1d, w2d))):
    R[nm] = {}
    for p, (s, e) in pers.items():
        m = (E.index >= s) & (E.index <= e)
        R[nm][p] = {k: round(float(((a[k] - b[k]) * E[k])[m].mean() * 252), 5) for k in P.MK}
ac = {}
for k in P.MK:
    for p, (s, e) in pers.items():
        x = E[k][(E.index >= s) & (E.index <= e)]; x = x[x != 0]
        ac.setdefault(k, {})[p] = round(float(x.autocorr(1)), 4)
R['autocorr1'] = ac
g = P.src['GOLD']; g = g[(g.index >= '1985-01-01') & (g.index <= '2014-12-31')]
R['gold_zero_ret_days'] = {str(y): int((g[g.index.year == y] == 0).sum()) for y in range(1985, 2015, 3)}
json.dump(R, open(OUT, 'w'), indent=1)
