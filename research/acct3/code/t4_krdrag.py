# Implied yearly drag of KR-listed NDX 2x ETFs vs the ISA model (2r - rf - d), from public NAV period returns (funetf, 2026-11-03)
# and FRED NASDAQ100 (price), DTB3, DEXKOUS. Only the product drag is reported (no strategy result on post-2014 data).
import sys, pandas as pd, numpy as np
from scipy.optimize import brentq
d = '/tmp/claude-0/acct3/fred/'
nd = pd.read_csv(d + 'NASDAQ100.csv', index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors='coerce').dropna()
rf = pd.read_csv(d + 'DTB3.csv', index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors='coerce').ffill() / 100
fx = pd.read_csv(d + 'DEXKOUS.csv', index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors='coerce').ffill()
def us_close_before(kr_date):
    return nd.index[nd.index < pd.Timestamp(kr_date)][-1]
def model(a, b, drag, hedged):
    s = nd.loc[a:b]; r = s.pct_change().dropna(); f = rf.reindex(r.index).ffill().bfill()
    dt = np.r_[1, np.diff(s.index.values).astype('timedelta64[D]').astype(float)][1:]   # calendar days for financing
    g = np.prod(1 + 2 * r.values - f.values * dt / 365 - drag * dt / 365)
    if not hedged: g *= fx.asof(b) / fx.asof(a)
    return g - 1
end = '2026-11-03'
cases = [('KODEX 409820 (H)', True, {'1Y': ('2025-11-03', 6.21), '3Y': ('2023-11-03', 165.22), '상장이후': ('2021-12-09', 76.39)}),
         ('TIGER 418660 (UH)', False, {'1Y': ('2025-11-03', -5.1), '3Y': ('2023-11-03', 189.15), '상장이후': ('2022-02-22', 239.07)})]
for nm, h, W in cases:
    for k, (st, nav) in W.items():
        a = us_close_before(st); b = us_close_before(end); yrs = (b - a).days / 365.25
        f = lambda dr: model(a, b, dr, h) - nav / 100
        dimp = brentq(f, -0.5, 0.5)
        print('%-18s %-5s %s~%s NAV %+7.2f%%  model(drag0) %+7.2f%%  model(drag 2.45%%) %+7.2f%%  implied drag %.2f%%/yr' % (
            nm, k, a.date(), b.date(), nav, 100 * model(a, b, 0, h), 100 * model(a, b, .0245, h), 100 * dimp))
# hypothesis B for the unhedged product: daily 2x of the KRW-converted index (2x FX exposure)
def modelB(a, b, drag):
    s = nd.loc[a:b]; x = fx.reindex(s.index).ffill().bfill(); k = (s * x)
    r = k.pct_change().dropna(); f = rf.reindex(r.index).ffill().bfill()
    dt = np.diff(s.index.values).astype('timedelta64[D]').astype(float)
    return np.prod(1 + 2 * r.values - f.values * dt / 365 - drag * dt / 365) - 1
for k, (st, nav) in cases[1][2].items():
    a = us_close_before(st); b = us_close_before(end)
    dimp = brentq(lambda dr: modelB(a, b, dr) - nav / 100, -0.5, 0.5)
    print('TIGER UH hypB (2x KRW index) %-5s NAV %+7.2f%% model0 %+7.2f%% implied drag %.2f%%/yr' % (k, nav, 100 * modelB(a, b, 0), 100 * dimp))
# same yardstick for TQQQ (Twelve Data closes, split-adjusted, dividends ignored = slightly conservative): 3r - 2rf - d
def model3(a, b, drag):
    s = nd.loc[a:b]; r = s.pct_change().dropna(); f = rf.reindex(r.index).ffill().bfill()
    dt = np.diff(s.index.values).astype('timedelta64[D]').astype(float)
    return np.prod(1 + 3 * r.values - 2 * f.values * dt / 365 - drag * dt / 365) - 1
for k, a, b, p0, p1 in (('3Y', '2023-11-02', '2026-11-02', 18.15, 59.46), ('2021-12-08~', '2021-12-08', '2026-11-02', 42.4425, 59.46)):
    tr = p1 / p0 - 1; a = pd.Timestamp(a); b = pd.Timestamp(b)
    dimp = brentq(lambda dr: model3(a, b, dr) - tr, -0.5, 0.5)
    print('TQQQ %-12s actual %+7.2f%% model(drag0) %+7.2f%% model(2.45%%) %+7.2f%% implied drag %.2f%%/yr' % (k, 100 * tr, 100 * model3(a, b, 0), 100 * model3(a, b, .0245), 100 * dimp))
