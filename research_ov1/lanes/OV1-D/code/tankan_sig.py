"""OV1-D signal library (frozen by PRECOMMIT.md). <=2014 only. N = 1 variant, no parameter search.
releases(cal)        -> DataFrame, one row per Tankan survey quarter whose usable day lies on the calendar:
                        quarter, surprise (NaN allowed), u (trading day), n_prior, thr (NaN if < 20 prior or surprise NaN), on_rel
on_daily(cal, rel)   -> bool Series on a trading-date index: on_rel of the latest release with u <= t (False before any)
step_series(cal, rel)-> (S, F, T) daily Series on cal for the HEADLINE path treatment:
                        S = cumulative surprise stepping on each u (NaN surprise steps 0), F = 1 on every release day,
                        T = thr on release days with a threshold, -1e9 on release days without one (sentinel -> OFF), ffilled
on_path(basis, S, F, T) -> (P,T) bool via ov1lib: latest surprise = jump of L.path_series(S) on the last path day j <= t with
                        L.gather(F) = 1, ON iff jump <= L.gather(T) on that day. Path day 0 has no jump -> no information (OFF).
Surprise_q = mean over (large mfg, large electrical machinery) of Actual DI(q) - Forecast DI(q); the forecast for target q was
published in the survey of q-1. 2004Q1 = NaN (BoJ continuity break). U_q = first trading day on/after the 1st of the 2nd month
after q's end month. thr_q = np.percentile(valid surprises with u < u_q, 33.33) (numpy default 'linear'), needs >= 20 of them.
ON iff surprise_q <= thr_q."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-D/'
CUT = LANE + 'data/boj_tankan_cut_le2014.csv'
END = pd.Timestamp('2014-12-31')
Q_PCT, MIN_PRIOR, NO_THR = 33.33, 20, -1e9

def calendar():
    R, M = jp.calendar('1928-01-03', '2014-12-31'); return R.index

def releases(cal):
    c = pd.read_csv(CUT)
    assert pd.to_datetime(c['quarter_end']).max() <= END
    s = ((c['actual_mfg'] - c['forecast_mfg']) + (c['actual_el'] - c['forecast_el'])) / 2
    s[c['quarter_code'] == 200401] = np.nan
    chk = (s - c['surprise_q']).abs(); assert (chk.fillna(0) == 0).all() and (s.isna() == c['surprise_q'].isna()).all()
    ucal = pd.to_datetime(c['usable_from_calendar']).values
    pos = cal.searchsorted(ucal)                               # first trading day on/after the calendar usable date
    ok = pos < len(cal)                                        # 2014Q4 (u in 2015) is dropped: never usable in sample
    r = pd.DataFrame(dict(quarter=c['quarter_code'].values[ok], surprise=s.values[ok], u=cal[pos[ok]]))
    assert r['u'].is_monotonic_increasing and r['u'].is_unique and r['u'].max() <= END
    thr = np.full(len(r), np.nan); npr = np.zeros(len(r), int)
    for k in range(len(r)):
        prior = r['surprise'].values[:k][~np.isnan(r['surprise'].values[:k])]   # u strictly earlier (u unique, sorted)
        npr[k] = len(prior)
        if len(prior) >= MIN_PRIOR and np.isfinite(r['surprise'].values[k]):
            thr[k] = np.percentile(prior, Q_PCT)
    r['n_prior'] = npr; r['thr'] = thr
    r['on_rel'] = np.isfinite(r['thr'].values) & (r['surprise'].values <= np.where(np.isfinite(thr), thr, -np.inf))
    return r

def on_daily(cal, rel):
    j = np.searchsorted(rel['u'].values, cal.values, side='right') - 1
    on = np.where(j >= 0, rel['on_rel'].values[np.maximum(j, 0)], False)
    return pd.Series(on.astype(bool), index=cal)

def step_series(cal, rel):
    S = pd.Series(0.0, index=cal); F = pd.Series(0.0, index=cal); T = pd.Series(np.nan, index=cal)
    for _, x in rel.iterrows():
        S.loc[x['u']] += x['surprise'] if np.isfinite(x['surprise']) else 0.0
        F.loc[x['u']] = 1.0; T.loc[x['u']] = x['thr'] if np.isfinite(x['thr']) else NO_THR
    return S.cumsum(), F, T.ffill()

def on_path(basis, S, F, T):
    sys.path.insert(0, '/mnt/project-files/research/ov1/code'); import ov1lib as L
    Sp = L.path_series(S, basis); Fg = L.gather(F, basis); Tg = L.gather(T, basis)
    jump = np.full(Sp.shape, np.nan); jump[:, 1:] = Sp[:, 1:] - Sp[:, :-1]
    isrel = Fg == 1
    with np.errstate(invalid='ignore'): relon = isrel & (jump <= Tg)
    idx = np.where(isrel, np.arange(Sp.shape[1])[None, :], -1); idx = np.maximum.accumulate(idx, axis=1)
    on = np.take_along_axis(relon, np.maximum(idx, 0), axis=1) & (idx >= 0)
    return on

def overlay(B, on):
    B = np.asarray(B, float); return np.where((B == 3) & on, 1.0, B)
