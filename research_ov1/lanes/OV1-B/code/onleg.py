"""OV1-B overnight leg on_t = O_t / C_{t-1} - 1 (raw split-adjusted, not dividend-adjusted prices), PRECOMMIT.md section 3.
Every loader cuts rows to <= `upto` (default 2014-12-31) right after reading, before anything is derived."""
import numpy as np, pandas as pd
D = '/mnt/project-files/research/ov1/lanes/OV1-B/data/'
END = pd.Timestamp('2014-12-31')


def _load(fn, upto):
    s = pd.read_csv(D + fn, parse_dates=['date']).set_index('date').sort_index()
    upto = min(pd.Timestamp(upto), END)
    return s[s.index <= upto][['open', 'close']].astype(float)


def qqq_td(upto=END): return _load('qqq_1day_cut_le20141231.csv', upto)
def qqq_panel(upto=END): return _load('qqq_panel_xcheck_le20141231.csv', upto)
def spy_panel(upto='1999-12-31'): return _load('spy_panel_19930129_19991231.csv', upto)


def raw_on(px, cal):
    """on_t on the trading calendar `cal` (DatetimeIndex, jp NDX calendar). NaN where px lacks t or the previous cal date.
    Also returns stale-open flags (O_t == C_{t-1})."""
    cal = pd.DatetimeIndex(cal)
    o = px['open'].reindex(cal); c = px['close'].reindex(cal)
    cprev = c.shift(1)
    on = o / cprev - 1.0
    stale = (o == cprev)
    return on, stale


def on_series(cal, upto=END, xcheck=True):
    """PRIMARY overnight leg (Twelve Data QQQ) with the pre-registered quality rules; NaN-free (0 = not covered).
    Returns (on Series on cal, info dict of counts)."""
    cal = pd.DatetimeIndex(cal); cal = cal[cal <= min(pd.Timestamp(upto), END)]
    td = qqq_td(upto)
    on, stale = raw_on(td, cal)
    covered = on.notna()
    info = dict(cal_days=int(len(cal)), covered_raw=int(covered.sum()), stale_open=int((stale & covered).sum()),
                first_cov=str(on[covered].index.min().date()) if covered.any() else '', last_cov=str(on[covered].index.max().date()) if covered.any() else '')
    big = covered & (on.abs() > 0.25)
    info['rule_a_abs_gt_25pct'] = int(big.sum()); on[big] = np.nan
    if xcheck:
        pn, _ = raw_on(qqq_panel(upto), cal)
        both = on.notna() & pn.notna()
        dis = both & ((on - pn).abs() > 0.005)
        info['xcheck_days_both'] = int(both.sum()); info['rule_b_disagree_gt_0.5pp'] = int(dis.sum())
        info['xcheck_max_abs_diff'] = float((on - pn)[both].abs().max()) if both.any() else float('nan')
        info['xcheck_n_diff_gt_1e-4'] = int(((on - pn)[both].abs() > 1e-4).sum())
        on[dis] = np.nan
    on = on.fillna(0.0)
    info['covered_final'] = int((on != 0).sum())
    return on, info


def on_ctx(on, dates, ii):
    """split travels with its source day: ON[i, j] = on[source day ii[i, j]]; ON[:, 0] = 0 (as ctx r[:, 0] = 0)."""
    v = pd.Series(on).reindex(pd.DatetimeIndex(dates)).fillna(0.0).values.astype(np.float64)
    ON = v[ii].copy(); ON[:, 0] = 0.0
    return ON
