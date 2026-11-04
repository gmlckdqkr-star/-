import numpy as np, pandas as pd
import deletion as D
S = D.sleeve('DEL', 60); car = S['car']
ev = [(t0, j) for t0, j in D.events('DEL') if t0 + 2 < D.T and np.isfinite(D.adj[t0 + 2, j])]
print('n', len(ev), len(car))
o = np.argsort(-car)[:12]
for k in o:
    t0, j = ev[k]; e = t0 + 2; rr = D.r[e + 1:e + 61, j]
    print(D.dates[t0].date(), 'car %.2f' % car[k], 'max1d %.2f' % np.nanmax(rr), 'min1d %.2f' % np.nanmin(rr), 'r250pre %.2f' % (D.adj[t0, j] / D.adj[max(t0 - 250, 0), j] - 1))
# contribution: drop top 5/10 events (winner removal)
idx = np.nonzero((D.dates >= '1986-01-02'))[0]; n = S['net'][idx]
print('daily ret > 50%:', np.sum(np.abs(np.nan_to_num(D.r[1:])) > 0.5), 'of which in DEL holds?')
big = np.abs(S['gross'][idx]) > 0.2; print('sleeve days |r|>20%:', big.sum(), [str(D.dates[idx][i].date()) for i in np.nonzero(big)[0][:20]])
