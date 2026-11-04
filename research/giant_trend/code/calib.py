"""Daily-reset vs monthly synthetic leverage gap on S&P TR 1928-2014 (same costs). Positive gap = monthly too generous."""
import numpy as np, pandas as pd, json
d = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/SPX_TR_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
tb = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/TBILL_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
d = d[(d.index >= '1928-01-01') & (d.index <= '2014-12-31')]
r = d['tr_ret'].astype(float).fillna(0)
rate = tb['rate_known_pct'].reindex(r.index).ffill() / 100
rfd = rate / 252
out = {}
for L, drag in ((2, .017), (3, .0245)):
    x = np.maximum(L * r - (L - 1) * rfd - drag / 252, -0.99)
    daily_lr = np.log1p(x)
    mr = (1 + r).groupby(r.index.to_period('M')).prod() - 1
    mrf = (1 + rfd).groupby(r.index.to_period('M')).prod() - 1
    mx = np.maximum(L * mr - (L - 1) * mrf - drag / 12, -0.99)
    dl = daily_lr.groupby(r.index.to_period('M')).sum()
    res = {}
    for a, b in (('1928-01', '1969-12'), ('1970-01', '2014-12'), ('1986-01', '2014-12'), ('1955-01', '1985-12')):
        m = (dl.index >= pd.Period(a)) & (dl.index <= pd.Period(b))
        yrs = m.sum() / 12
        gd = np.exp(dl[m].sum() / yrs) - 1; gm = np.exp(np.log1p(mx[m]).sum() / yrs) - 1
        res[f'{a}..{b}'] = dict(daily=round(gd, 4), monthly=round(gm, 4), gap=round(gm - gd, 4))
    out[L] = res
print(json.dumps(out, indent=1)); json.dump(out, open('../results/calib.json', 'w'), indent=1)
