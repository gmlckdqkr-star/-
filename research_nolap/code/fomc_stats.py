"""N1 event-day return stats + placebo (pre-1994 meeting days, no announcement)."""
import numpy as np, pandas as pd, json
from common import *
R, M = jp.calendar('1984-01-03', '2014-12-31'); XN = jp.mkX(R, M, 'NDX')
R, M = jp.calendar('1928-01-03', '1985-12-31'); XS = jp.mkX(R, M, 'SPX')
def st(X, days, a, b, lab):
    r = X['r']; r = r[(r.index >= a) & (r.index <= b)]
    d = pd.DatetimeIndex(days); d = d[(d >= a) & (d <= b)]
    e = r.reindex(d).dropna(); prev = r.shift(-1).reindex(d).dropna()  # prev: return of day before event
    e2 = r[r.index.isin(d)]; idx = r.index.get_indexer(e2.index); p = r.iloc[idx - 1]
    o = dict(lab=lab, n=int(len(e2)), ev_mean=float(e2.mean()), ev_sd=float(e2.std()), all_mean=float(r.mean()),
             t=float((e2.mean() - r.mean()) / (e2.std() / np.sqrt(len(e2)))), prevday_mean=float(p.mean()),
             two_day_mean=float((e2.values + p.values).mean()), hit=float((e2 > 0).mean()), all_hit=float((r > 0).mean()))
    print(' '.join('%s=%s' % (k, ('%.5f' % v) if isinstance(v, float) else v) for k, v in o.items())); return o
ann = fomc_days('1994-02-04', '2014-12-31'); pla = fomc_days('1980-01-01', '1994-01-31')
out = [st(XN, ann, '1994-02-04', '2014-12-31', 'NDX ann 94-14'), st(XN, ann, '1994-02-04', '2004-12-31', 'NDX ann 94-04'),
       st(XN, ann, '2005-01-01', '2014-12-31', 'NDX ann 05-14'), st(XN, ann, '2012-01-01', '2014-12-31', 'NDX ann 12-14'),
       st(XN, pla, '1986-01-02', '1994-01-31', 'NDX placebo 86-93'), st(XS, pla, '1980-01-01', '1985-12-31', 'SPX placebo 80-85')]
json.dump(out, open(RES + '/n1_fomc_stats.json', 'w'), indent=1)
