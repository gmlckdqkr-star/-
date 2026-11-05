"""Step 1: data-quality inspection + synthetic code test only (no labels, no returns, no v1 states, no signal on/fire dates)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-F/code'); sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import std, sig_f, jp  # noqa (std sets paths)
LANE = sig_f.LANE; out = {}
s = sig_f.raw(); sd = s.dropna()
out['raw'] = dict(first=str(s.index[0].date()), last=str(s.index[-1].date()), n_rows=int(len(s)), n_nan=int(s.isna().sum()),
                  n_values=int(len(sd)), min=float(sd.min()), max=float(sd.max()), n_nonpositive=int((sd <= 0).sum()),
                  dup_dates=int(s.index.duplicated().sum()))
gap = pd.Series(sd.index).diff().dt.days; out['raw']['max_calendar_gap_days'] = int(gap.max())
out['raw']['gaps_gt_5d'] = [str(sd.index[i].date()) for i in np.where(gap.values > 5)[0]]
dl = np.log(sd).diff().dropna(); big = dl[dl.abs() > 0.04]
out['raw']['abs_daily_logchg_q'] = [float(x) for x in dl.abs().quantile([.5, .99, .999]).values]
out['raw']['daily_logchg_abs_gt_4pct'] = {str(a.date()): round(float(b), 4) for a, b in big.items()}   # data-error screen only
out['raw']['n_unchanged_days_1971_1973'] = int((dl[(dl.index < '1973-03-01')].abs() < 1e-12).sum())
cal = sig_f.master_cal(); lx = sig_f.onto(sig_f.log_avail(), cal)
out['master_cal'] = dict(first=str(cal[0].date()), last=str(cal[-1].date()), n=int(len(cal)))
i0 = int(np.argmax(~np.isnan(lx))); out['first_avail_trading_day'] = str(cal[i0].date())
out['nan_after_first_avail'] = int(np.isnan(lx[i0:]).sum())
# validity start only (counts, no values): yen21 defined from i0+21, threshold needs 756 defined yen21 strictly before t
y_first = i0 + sig_f.H; thr_first = y_first + sig_f.W
out['first_yen21_day'] = str(cal[y_first].date()); out['first_signal_defined_day'] = str(cal[thr_first].date())
# stale FX values on equity trading days (FX holiday but NYSE open -> previous value carried)
st = pd.Series(lx[i0:], index=cal[i0:]); ch = st.diff().iloc[1:]
out['equity_days_with_carried_fx_value_share'] = float((ch.abs() < 1e-15).mean())
# calendars of each basis are subsets of the master calendar
import ov1lib as L
out['basis_cal_subset_of_master'] = {k: bool(v.isin(cal).all()) for k, v in L.dates().items()}
# synthetic test of the threshold code vs brute force numpy.percentile (random data with NaN gaps) - code path only
g = np.random.default_rng(5); Z = g.standard_normal((3, 2500)); Z[0, 100:130] = np.nan; Z[1, 1500] = np.nan; Z[2, :10] = np.nan
Z[2, 700:900] = np.round(Z[2, 700:900], 1)                   # ties
mx = 0.0; nn_mis = 0
for i in range(3):
    th = sig_f._thr_row(Z[i].copy(), sig_f.W, sig_f.Q)
    for t in range(Z.shape[1]):
        w = Z[i, max(t - sig_f.W, 0):t]
        bf = np.percentile(w, 95) if (t >= sig_f.W and not np.isnan(w).any()) else np.nan
        if np.isnan(bf) != np.isnan(th[t]): nn_mis += 1
        elif not np.isnan(bf): mx = max(mx, abs(bf - th[t]))
out['synthetic_thr_check'] = dict(max_abs_diff=mx, nan_pattern_mismatches=nn_mis)
lxs = np.cumsum(g.standard_normal((2, 2000)) * 0.01, axis=1); S = sig_f.signal_rows(lxs)
f = S['fire']; on = S['on']; ob = np.zeros_like(on)
for i in range(2):
    for t in range(2000): ob[i, t] = f[i, max(0, t - 20):t + 1].any()
out['synthetic_hold_check_mismatch'] = int((ob != on).sum())
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(LANE + 'results/s1_inspect.json', 'w'), indent=1, default=str)
