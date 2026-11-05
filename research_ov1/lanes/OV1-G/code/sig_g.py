"""OV1-G signal library: off-meeting Fed funds target CUT -> 42-trading-day ON window (frozen by PRECOMMIT.md). <=2014 only.
Inputs: data/cut_DFEDTAR.csv (1982-09-27..2008-12-15), data/cut_DFEDTARU.csv / cut_DFEDTARL.csv (2008-12-16..2014-12-31),
        data/fomc_events_1982_2014.csv (parsed federalreserve.gov historical pages: meeting / conference_call / unscheduled days).
Event rule (PRECOMMIT section 4):
  cut day d  : DFEDTAR(d) < DFEDTAR(previous row)   [DFEDTARU/DFEDTARL after 2008-12-16: change of either bound downward]
  S          : every day of every scheduled 'Meeting' heading
  DA         : the first weekday (Mon-Fri) after the LAST day of each scheduled meeting ('the day after')
  C          : conference-call and unscheduled-meeting days
  off-meeting: d not in S AND (d not in DA OR d in C)
  usable u   : d <  1994-02-04 -> first trading day of `cal` strictly after d (unannounced era, +1 trading day)
               d >= 1994-02-04 -> first trading day of `cal` on or after d (announced the same day, before the close)
  ON(t)      : some event has u in positions [t-41, t] of the row (42 trading-day closes starting at u)."""
import datetime as dt, numpy as np, pandas as pd
D = '/mnt/project-files/research/ov1/lanes/OV1-G/data/'
END = pd.Timestamp('2014-12-31'); ANN = pd.Timestamp('1994-02-04'); HOLD = 42

def _rd(fn, col):
    s = pd.read_csv(D + fn, parse_dates=['observation_date']).set_index('observation_date')[col].astype(float)
    s = s[s.index <= END]; assert s.index.is_unique and s.index.is_monotonic_increasing; return s

def fomc_sets():
    ev = pd.read_csv(D + 'fomc_events_1982_2014.csv', parse_dates=['date']); ev = ev[ev.date <= END]
    S = set(ev.loc[ev.kind == 'meeting', 'date'])
    last = ev[(ev.kind == 'meeting') & (ev.day_of_event == ev.n_days)].date
    DA = set()
    for x in last:
        y = x + pd.Timedelta(days=1)
        while y.weekday() >= 5: y += pd.Timedelta(days=1)
        DA.add(y)
    C = set(ev.loc[ev.kind.isin(['conference_call', 'unscheduled']), 'date'])
    return S, DA, C

def cuts():
    """DataFrame of every target cut: date, old, new, kind ('off' | 'meeting')."""
    t = _rd('cut_DFEDTAR.csv', 'DFEDTAR'); u = _rd('cut_DFEDTARU.csv', 'DFEDTARU'); l = _rd('cut_DFEDTARL.csv', 'DFEDTARL')
    S, DA, C = fomc_sets(); rows = []
    dt_ = t.diff()
    for d, x in dt_[dt_ < 0].items(): rows.append((d, float(t.shift(1)[d]), float(t[d])))
    for s in (u, l):                       # after 2008-12-16 (the 2008-12-16 switch to a range is the start, not a change)
        ds = s.diff()
        for d, x in ds[ds < 0].items(): rows.append((d, float(s.shift(1)[d]), float(s[d])))
    rows = sorted(set(rows))
    out = []
    for d, o, n in rows:
        off = (d not in S) and ((d not in DA) or (d in C))
        out.append(dict(date=d, old=o, new=n, kind='off' if off else 'meeting', in_S=d in S, in_DA=d in DA, in_C=d in C))
    return pd.DataFrame(out)

def events(cal, pit_extra=0, include_meeting=False):
    """Off-meeting cut events with usable dates on trading calendar `cal` (DatetimeIndex).
    pit_extra: extra trading days of lag for pre-1994 events (information-only sensitivity; 0 = frozen rule).
    include_meeting: True only for the information-only control (all cuts)."""
    c = cuts()
    if not include_meeting: c = c[c.kind == 'off']
    c = c[c.date >= cal[0]]               # a calendar that starts after the change date does not cover it
    us = []
    for d in c.date:
        if d < ANN: k = cal.searchsorted(d, side='right') + pit_extra
        else: k = cal.searchsorted(d, side='left')
        us.append(cal[k] if k < len(cal) else pd.NaT)
    c = c.copy(); c['usable'] = us
    return c[c.usable.notna() & (c.usable <= END)].reset_index(drop=True)

def first_day():
    return _rd('cut_DFEDTAR.csv', 'DFEDTAR').index.min()

def count_series(cal, **kw):
    """Cumulative number of usable events on `cal` (NaN before the first DFEDTAR date = not covered)."""
    e = events(cal, **kw); ind = pd.Series(0.0, index=cal)
    for u in e.usable: ind[u] += 1.0
    cnt = ind.cumsum(); cnt[cal < first_day()] = np.nan
    return cnt

def on_rows(CNT):
    """CNT: (P,T) cumulative count along each row (path-rebuilt or real). ON(t) = an event in positions [t-41, t].
    Position 0 of a row has no usable change (path rebuild sets its diff to 0). NaN (not covered) -> off."""
    A = np.asarray(CNT, float); inc = np.zeros(A.shape); inc[:, 1:] = np.diff(A, axis=1)
    inc = np.where(np.isnan(inc), 0.0, inc)
    cs = np.cumsum(inc, axis=1); lag = np.zeros(A.shape); lag[:, HOLD:] = cs[:, :-HOLD]
    on = (cs - lag) > 0.5
    return on & ~np.isnan(A)

def on_series(cal, **kw):
    cnt = count_series(cal, **kw)
    return pd.Series(on_rows(cnt.values[None, :])[0], index=cal)
