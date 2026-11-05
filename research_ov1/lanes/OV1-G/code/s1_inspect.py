"""OV1-G step 1: DATA-ONLY inspection (no returns, labels, v1 states or strategy values are read).
Lists every DFEDTAR change (date, old, new), the nearest FOMC event days, and DFEDTARU/L changes 2008-12-16..2014-12-31.
Uses only the NDX/SPX trading-calendar index (dates) from jp.calendar, never the return columns."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa  (std sets the MS1 import paths)
D = '/mnt/project-files/research/ov1/lanes/OV1-G/data/'; END = pd.Timestamp('2014-12-31')
t = pd.read_csv(D + 'cut_DFEDTAR.csv', parse_dates=['observation_date']).set_index('observation_date')['DFEDTAR'].astype(float)
u = pd.read_csv(D + 'cut_DFEDTARU.csv', parse_dates=['observation_date']).set_index('observation_date')['DFEDTARU'].astype(float)
l = pd.read_csv(D + 'cut_DFEDTARL.csv', parse_dates=['observation_date']).set_index('observation_date')['DFEDTARL'].astype(float)
assert t.index.max() <= END and u.index.max() <= END
ev = pd.read_csv(D + 'fomc_events_1982_2014.csv', parse_dates=['date'])
cal_days = pd.date_range(t.index.min(), t.index.max())
gaps = cal_days.difference(t.index)
R, M = jp.calendar('1984-01-03', '2014-12-31'); ndx_cal = jp.mkX(R, M, 'NDX').index
R2, M2 = jp.calendar('1928-01-03', '1985-12-31'); spx_cal = jp.mkX(R2, M2, 'SPX').index
cal = spx_cal[spx_cal < ndx_cal[0]].append(ndx_cal)
d = t.diff(); ch = d[d.fillna(0) != 0]
rows = []
for dd, delta in ch.items():
    prev = ev[ev.date <= dd].tail(3); nxt = ev[ev.date > dd].head(1)
    on_ev = ev[ev.date == dd]
    rows.append(dict(date=str(dd.date()), dow=dd.day_name()[:3], old=float(t.shift(1)[dd]), new=float(t[dd]), delta=float(delta),
                     trading_day=bool(dd in cal),
                     same_day_event=';'.join(on_ev.kind + ':' + on_ev.heading) if len(on_ev) else '',
                     prev_events=' | '.join('%s %s' % (str(r.date.date()), r.kind) for r in prev.itertuples()),
                     next_event=' | '.join('%s %s' % (str(r.date.date()), r.kind) for r in nxt.itertuples())))
df = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90); pd.set_option('display.max_rows', 400)
print('DFEDTAR rows', len(t), t.index.min().date(), t.index.max().date(), 'calendar-day gaps', len(gaps))
print('changes', len(df), 'cuts', int((df.delta < 0).sum()), 'hikes', int((df.delta > 0).sum()))
print(df.to_string(index=False))
du = u.diff().fillna(0); dl = l.diff().fillna(0)
print('DFEDTARU changes 2008-12-16..2014-12-31:', int((du != 0).sum()), 'DFEDTARL changes:', int((dl != 0).sum()),
      'levels U', sorted(u.unique()), 'L', sorted(l.unique()))
print('non-meeting FOMC kinds:', ev.kind.value_counts().to_dict())
print(ev[ev.kind == 'unscheduled'].to_string(index=False))
json.dump(dict(dfedtar_rows=len(t), first=str(t.index.min().date()), last=str(t.index.max().date()), calendar_day_gaps=len(gaps),
               n_changes=len(df), changes=rows, dfedtaru_changes=int((du != 0).sum()), dfedtarl_changes=int((dl != 0).sum()),
               fomc_kinds=ev.kind.value_counts().to_dict()),
          open('/mnt/project-files/research/ov1/lanes/OV1-G/results/s1_inspect.json', 'w'), indent=1)
