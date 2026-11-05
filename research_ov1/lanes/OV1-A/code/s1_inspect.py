"""OV1-A step 1: data inspection only (no labels, no strategy returns, no signal on-dates). <=2014."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
CSV = '/mnt/project-files/research/ov1/lanes/OV1-A/data/noise_hpw_cut_le2014.csv'
n = pd.read_csv(CSV, parse_dates=['Date']).set_index('Date')['Noise_bp']
assert n.index.max() <= pd.Timestamp('2014-12-31') and n.index.is_unique and n.index.is_monotonic_increasing
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); cal = X.index
out = {}
out['rows'] = int(len(n)); out['first'] = str(n.index[0].date()); out['last'] = str(n.index[-1].date())
out['nan'] = int(n.isna().sum()); out['nonpos'] = int((n <= 0).sum())
off = n.index.difference(cal); out['off_calendar_dates'] = [str(d.date()) for d in off]
c87 = cal[cal >= n.index[0]]; miss = c87.difference(n.index); out['ndx_days_from_first'] = int(len(c87)); out['ndx_days_missing'] = int(len(miss))
m = pd.Series(1, index=c87); m[miss] = 0; run = (m == 0).astype(int); g = (run.diff() != 0).cumsum(); out['longest_missing_run'] = int(run.groupby(g).sum().max())
# PIT rule (chosen): drop off-calendar dates, value dated d usable from next NDX day (shift 1), ffill limit 5
s = n.reindex(cal).shift(1).ffill(limit=5)
out['Nstar_first_valid'] = str(s.first_valid_index().date()); out['Nstar_nan_after_first'] = int(s[s.first_valid_index():].isna().sum())
cnt = s.notna().rolling(252).sum(); out['first_252_full'] = str(cnt[cnt >= 252].index[0].date())
out['noise_desc'] = {k: float(v) for k, v in s.describe().items()}
out['noise_yearly_median'] = {int(y): round(float(v), 3) for y, v in s.groupby(s.index.year).median().dropna().items()}
v = X['vix']; out['vix_first_valid'] = str(v.first_valid_index().date()); out['vix_nan_86_14'] = int(v['1986-01-02':].isna().sum())
out['vix_yearly_nan'] = {int(y): int(k) for y, k in v.isna().groupby(v.index.year).sum().items() if k > 0}
out['vix_desc'] = {k: float(x) for k, x in v.describe().items()}
print(json.dumps(out, indent=1))
json.dump(out, open('/mnt/project-files/research/ov1/lanes/OV1-A/results/s1_inspect.json', 'w'), indent=1)
