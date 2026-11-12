"""C2: long-run data retention of the app's v1 inputs. Runs the app's own market_history.py + v1_signal.py (PC copies)
with a fake clock, a fake broker (QQQ closes <=2014, last 800 rows per read like CLOSE_ROWS_WANTED) and the Treasury CSVs.
Scenarios: (a) nothing happens; (b) the broker restates past closes once (x0.995 before the event, like a dividend/split adjustment);
(c) the phone loses market_history.json (+ .bak) only; (d) it loses both files (+ .bak), e.g. app data cleared / fresh install."""
import sys, os, glob, json, shutil, tempfile, calendar as cal, datetime as dt, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/claude-0/ru1_app'); sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
from ait_accounts import v1_signal as V
from account_slots import market_history as MH
import mkt
END = pd.Timestamp('2014-12-31')
q = mkt.pser('QQQ', 3); q = q[q.index <= END]
CMT = {}
for f in sorted(glob.glob('/mnt/project-files/research/ru1/data/tr*.csv')): CMT.update(V.parse_treasury_csv(open(f).read()))
def rate_fetcher(year):
    d = {k: v for k, v in CMT.items() if k.startswith(str(year))}
    if not d: raise MH.HistoryError('TREASURY_EMPTY')
    return d
EVENT = pd.Timestamp('2012-06-01'); START = pd.Timestamp('2010-01-04')
def run(scn):
    tmp = tempfile.mkdtemp(); hp = os.path.join(tmp, 'market_history.json'); sp = os.path.join(tmp, 'v1_state.json')
    state = {'now': 0.0}
    clock = lambda: state['now']
    days = q.index[(q.index >= START)]
    log = []; adjusted = False; done_event = False
    for i, d in enumerate(days):
        if i % 5: continue
        state['now'] = cal.timegm((d + pd.Timedelta(hours=15)).timetuple())   # 10:00 New York (summer) / 15:00 UTC
        if d >= EVENT and not done_event:
            done_event = True
            if scn == 'b': adjusted = True
            if scn in ('c', 'd'):
                for f in (hp, hp + '.bak'):
                    if os.path.exists(f): os.remove(f)
            if scn == 'd':
                for f in (sp, sp + '.bak'):
                    if os.path.exists(f): os.remove(f)
        cutoff = MH.time.strftime('%Y%m%d', MH.time.gmtime(state['now'] - 4 * 3600))
        cut = pd.Timestamp(cutoff)
        def fetch():
            s = q[q.index < cut].iloc[-800:]
            if adjusted: s = s.where(s.index >= EVENT, s * 0.995)
            return [(k.strftime('%Y-%m-%d'), float(v)) for k, v in s.items()]
        store = MH.MarketHistory(hp, clock=clock)
        def history():
            store.refresh({'QQQ': fetch}, rate_fetcher, cut.strftime('%Y-%m-%d'))
            return store.rows()
        prov = V.V1Provider(history, sp, today_fn=lambda: d.date())
        r = prov('slot1', 't%d' % i, {})
        log.append(dict(date=d.strftime('%Y-%m-%d'), status=r['status'], level=r.get('level'), start_after=(r.get('details') or {}).get('start_after'),
                        note=r['notes'][0][:90]))
    shutil.rmtree(tmp)
    return log
out = {}
for scn in ('a', 'b', 'c', 'd'):
    lg = run(scn); err = [x for x in lg if x['status'] != 'ok']; after = [x for x in lg if x['date'] >= EVENT.strftime('%Y-%m-%d')]
    starts = sorted({x['start_after'] for x in lg if x['start_after']})
    out[scn] = dict(calls=len(lg), errors=len(err), errors_after_event=sum(x['status'] != 'ok' for x in after), calls_after_event=len(after),
                    first_error=(err[0] if err else None), last_ok_before_error=next((x for x in reversed(lg) if err and x['status'] == 'ok' and x['date'] < err[0]['date']), None),
                    start_dates=starts, ok_after_event_levels=sorted({x['level'] for x in after if x['status'] == 'ok'}))
    print(scn, json.dumps({k: v for k, v in out[scn].items()}, ensure_ascii=False)[:900], flush=True)
json.dump(out, open('/mnt/project-files/research/ru1/results/c2_history.json', 'w'), indent=1, ensure_ascii=False)
