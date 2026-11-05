"""OV1-E step 1: data inspection only (no labels, no returns, no v1 states, no signal on-dates). <=2014 rows only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-E/code'); import sig_e  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-E/'
out = {}
cal = sig_e.master_cal()
for sid in ('DED3', 'DTB3', 'TEDRATE'):
    raw = pd.read_csv(sig_e.D + 'cut_%s_le2014.csv' % sid); raw.columns = ['date', 'v']
    s = sig_e.read_fred(sid); idx = s.index
    gaps = pd.Series(idx[1:] - idx[:-1]).dt.days
    off = idx.difference(cal)
    calr = cal[(cal >= idx[0]) & (cal <= sig_e.CUT)]; miss = calr.difference(idx)
    out[sid] = dict(rows_cut=int(len(raw)), valid=int(len(s)), blank_rows=int(len(raw) - len(s)), first=str(idx[0].date()),
                    last=str(idx[-1].date()), max_gap_calendar_days=int(gaps.max()), gaps_over_5d=int((gaps > 5).sum()),
                    obs_per_year_min=int(s.groupby(s.index.year).size().min()), obs_per_year_max=int(s.groupby(s.index.year).size().max()),
                    obs_dated_off_master_calendar=int(len(off)), master_days_without_obs=int(len(miss)),
                    min=float(s.min()), max=float(s.max()))
    if sid == 'DED3':
        out[sid]['obs_per_year'] = {int(y): int(n) for y, n in s.groupby(s.index.year).size().items()}
        big = gaps[gaps > 5]
        out[sid]['gaps_over_5d_list'] = [[str(idx[i].date()), str(idx[i + 1].date())] for i in big.index]
ted = sig_e.ted_star(cal)
out['TED_first_valid'] = str(ted.first_valid_index().date())
t = ted.dropna()
out['TED_desc'] = {k: float(v) for k, v in t.describe().items()}
out['TED_yearly_median'] = {int(y): round(float(v), 3) for y, v in t.groupby(t.index.year).median().items()}
out['TED_negative_days'] = int((t < 0).sum())
# definitional availability only (no on-dates): first master day where x(t) and the 1260-value trailing window are all defined
A = ted.values[None, :]
x = np.full(A.shape, np.nan); x[:, 63:] = A[:, 63:] - A[:, :-63]
xs = pd.Series(x[0], index=cal)
ok = xs.notna().astype(int).rolling(1260).sum().shift(1) >= 1260
first_def = xs.index[(ok & xs.notna()).values][0]
out['signal_first_defined_master'] = str(first_def.date())
out['x_desc_all_defined'] = {k: float(v) for k, v in xs.dropna().describe().items()}
# cross-check: DED3-based TED vs FRED TEDRATE (LIBOR - bill) on 1986-2014 common days (data quality only, never a signal)
tr = sig_e.lag1_onto(sig_e.read_fred('TEDRATE'), cal)
m = (cal >= pd.Timestamp('1986-01-03')) & ted.notna().values & tr.notna().values
out['xcheck_TEDRATE_1986_2014'] = dict(n=int(m.sum()), corr_level=float(np.corrcoef(ted[m], tr[m])[0, 1]),
                                      median_abs_diff=float(np.median(np.abs(ted[m] - tr[m]))),
                                      corr_63d_change=float(pd.concat([ted[m].diff(63), tr[m].diff(63)], axis=1).dropna().corr().iloc[0, 1]))
# MS1 calendars: does every basis date exist in the master calendar?
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); import ov1lib as L  # noqa
out['basis_dates_in_master'] = {k: bool(v.isin(cal).all()) for k, v in L.dates().items()}
out['basis_date_ranges'] = {k: [str(v[0].date()), str(v[-1].date()), int(len(v))] for k, v in L.dates().items()}
print(json.dumps(out, indent=1))
json.dump(out, open(LANE + 'results/s1_inspect.json', 'w'), indent=1)
