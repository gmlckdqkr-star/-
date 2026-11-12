# independent cross-check of the LH1 alarm fill (raw files, monthly logic, no ov/mkt code) + v1 exposure timeline
import os, sys, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
DH = '/mnt/project-files/research/data/deep_history/'
ie = pd.read_excel(DH + 'raw/ie_data.xls', sheet_name='Data', skiprows=7)
ie = ie[pd.to_numeric(ie['Date'], errors='coerce').notna()].copy()
d = ie['Date'].astype(float); yr = np.floor(d).astype(int); mo = np.round((d - yr) * 100).astype(int)
gs10 = pd.Series(pd.to_numeric(ie['Rate GS10'], errors='coerce').values, index=pd.to_datetime(dict(year=yr, month=mo, day=1)))
tb = pd.read_csv(DH + 'clean/TBILL_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
short_m = tb['rate_pct'].groupby(tb.index.to_period('M')).first(); short_m.index = short_m.index.to_timestamp()
cp = pd.read_csv('/mnt/project-files/research/lh1/data/M13002US35620M156NNBR_le1954.csv', parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0].astype(float)
# lookahead check: rate_known_pct on a date = previous month's rate_pct
k = tb.loc['1928-02-01':'1934-01-31']; pm = short_m.shift(1).reindex(k.index.to_period('M').to_timestamp()).values
print('rate_known_pct == prev-month rate_pct (1928-02..1934-01):', bool(np.allclose(k['rate_known_pct'].values, pm, atol=1e-9)), len(k))
for nm, s in (('A_tbill', short_m), ('B_cp', cp)):
    m = pd.DataFrame({'gs10': gs10, 's': s}).loc['1927-06-01':'1934-01-01'].dropna()
    inv = m.index[m['gs10'] < m['s']]
    print(nm, 'inverted months (known next month):', [str(x.date())[:7] for x in inv])
# exposure timeline from the engine (same as lh1run)
sys.path.insert(0, '/mnt/project-files/research/lh1/code'); import lh1run as L, ov, std
for fill in ('A', 'B'):
    X = L.build(L.END, fill); F = ov.flags_hist(X); c = ov.Ctx(X, F, np.arange(0, len(X))[None, :])
    B, bfn, bp, fs = std.s085(c); dates = X.index[L.W:]
    on = (F['inv'] | F['shock6m']); tr = on.astype(int).diff().fillna(0)
    print(fill, 'alarm switches <=1934:', [(str(i.date()), int(v)) for i, v in tr[(tr != 0) & (tr.index < '1934-06-01')].items()])
    tg = pd.Series(np.asarray(B).reshape(-1)[-len(dates):], index=dates) if np.asarray(B).size >= len(dates) else None
    if tg is not None:
        for a, b in (('1929-08-01', '1929-12-31'), ('1931-06-01', '1932-07-31')):
            s = tg.loc[a:b].resample('MS').mean().round(2); print(' ', fill, 'mean target by month', a[:7], '..', b[:7], s.to_dict())
