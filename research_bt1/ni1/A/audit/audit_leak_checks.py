# NI1-A audit: survivorship / membership / outlier / window checks. Numbers and codes only, no names.
import sys, json, collections
import numpy as np, pandas as pd
MC = '/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-%d.parquet'
DOCS, EV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
m = pd.concat([pd.read_parquet(MC % y, columns=['Code', 'Date', 'ChangesRatio', 'Market', 'Stocks', 'Volume'])
               for y in range(2002, 2010)])
m['ds'] = m.Date.dt.strftime('%Y%m%d')
res = {}
# 1. is marcap Market historical (point-in-time) or backfilled? codes that carry both labels over 2002-2009
lab = m.groupby('Code').Market.nunique()
res['codes_with_both_KOSPI_and_KOSDAQ_labels_2002_2009'] = int((lab > 1).sum())
# 2. events by current corp_cls (from list.json) -- included KOSPI-on-date events that are not 'Y' today
docs = {d['rcept_no']: d for d in map(json.loads, open(DOCS))}
E = pd.read_csv(EV, dtype={'rcept_no': str, 'rcept_dt': str, 'entry': str})
E['cls_now'] = [docs[r]['corp_cls'] for r in E.rcept_no]
res['included_events_by_corp_cls_now'] = E.groupby(['sig', 'cls_now']).size().unstack(fill_value=0).to_dict('index')
res['S1_mean_excess_by_cls_now'] = E[E.sig == 'S1'].groupby('cls_now').x.agg(['size', 'mean']).to_dict('index')
# 3. the dropped 'absent on rcept_dt' event and blank-code events
days = sorted(m.loc[m.Market == 'KOSPI', 'ds'].unique())
kos = set(zip(m.loc[m.Market == 'KOSPI', 'ds'], m.loc[m.Market == 'KOSPI', 'Code']))
anym = set(zip(m.ds, m.Code))
import bisect
ab = []
blank = []
for d in docs.values():
    if not d.get('parsed') or d['net'] == 0:
        continue
    c = (d['stock_code'] or '').strip()
    if len(c) != 6:
        blank.append(dict(sig='S1' if d['net'] > 0 else 'S2', cls_now=d['corp_cls'], rcept_dt=d['rcept_dt'])); continue
    dm = days[bisect.bisect_right(days, d['rcept_dt']) - 1]
    if (dm, c) not in kos and (dm, c) not in anym:
        g = m[m.Code == c]
        ab.append(dict(rcept_dt=d['rcept_dt'], first_row=str(g.Date.min().date()), last_row=str(g.Date.max().date()),
                       markets=sorted(g.Market.unique()), sig='S1' if d['net'] > 0 else 'S2'))
res['dropped_absent_on_rcept_dt'] = ab
res['dropped_blank_stock_code'] = blank
# 4. extreme daily ChangesRatio in KOSPI rows (listing / re-listing days) and their effect on the EW benchmark
k = m[m.Market == 'KOSPI']
res['kospi_rows_abs_changesratio_gt_15_5pct'] = int((k.ChangesRatio.abs() > 15.5).sum())
ew = k.groupby('ds').ChangesRatio.mean() / 100
ew_cap = k.assign(cr=k.ChangesRatio.clip(-15, 15)).groupby('ds').cr.mean() / 100
res['ew_daily_mean'] = float(ew.mean()); res['ew_daily_mean_capped_15pct'] = float(ew_cap.mean())
# zero-volume (halted) KOSPI rows included in EW
res['kospi_rows_zero_volume_share'] = float((k.Volume == 0).mean())
# 5. event outliers
S1 = E[E.sig == 'S1']
res['S1_top5_excess'] = sorted(S1.x.round(4).tolist())[-5:]
res['S1_bottom5_excess'] = sorted(S1.x.round(4).tolist())[:5]
res['S1_events_with_missing_days'] = S1[S1.nmiss > 0][['rcept_dt', 'nmiss', 'x']].to_dict('records')
# 6. events whose entry is AFTER rcept_dt by exactly 2 trading days; none enter on/before rcept_dt
res['entry_after_rcept_all'] = bool((E.entry > E.rcept_dt).all())
# 7. year coverage of the S1 KOSPI events vs. insider list (no gap months)
res['S1_events_per_year'] = S1.rcept_dt.str[:4].value_counts().sort_index().to_dict()
print(json.dumps(res, indent=1, default=str, ensure_ascii=False))
json.dump(res, open(OUT, 'w'), indent=1, default=str, ensure_ascii=False)
