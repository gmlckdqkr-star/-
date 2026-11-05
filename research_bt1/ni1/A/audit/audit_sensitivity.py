# NI1-A audit: context-only sensitivities (NOT gate inputs; the gate is fixed at entry t+2, 21 days, EW daily mean).
# entry lag 1..3 trading days, dating by rcept_no date, and S1 without its single largest event.
import sys, json, bisect
import numpy as np, pandas as pd
DOCS, EV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
MC = '/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-%d.parquet'
m = pd.concat([pd.read_parquet(MC % y, columns=['Code', 'Date', 'ChangesRatio', 'Market']) for y in range(2002, 2010)])
m['ds'] = m.Date.dt.strftime('%Y%m%d')
days = sorted(m.loc[m.Market == 'KOSPI', 'ds'].unique())
R = m.pivot(index='ds', columns='Code', values='ChangesRatio').reindex(days) / 100
K = (m.assign(k=(m.Market == 'KOSPI').astype(float)).pivot(index='ds', columns='Code', values='k').reindex(days) > 0)
ew = R.where(K).mean(axis=1).values
E = pd.read_csv(EV, dtype={'rcept_no': str, 'rcept_dt': str, 'entry': str})
docs = {d['rcept_no']: d for d in map(json.loads, open(DOCS))}
E['code'] = [docs[r]['stock_code'] for r in E.rcept_no]


def tstat(x):
    x = np.asarray(x); return dict(n=len(x), mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))))


def run(lag, use_no_date=False):
    out = {'S1': [], 'S2': []}
    for _, e in E.iterrows():
        rd = e.rcept_no[:8] if use_no_date else e.rcept_dt
        i = bisect.bisect_right(days, rd)        # first trading day > rd
        ie = i + lag - 1
        w = slice(ie + 1, ie + 22)
        rs = np.nan_to_num(R[e.code].values[w])
        out[e.sig].append(np.prod(1 + rs) - np.prod(1 + ew[w]))
    return {k: tstat(v) for k, v in out.items()}


res = {('lag%d' % L): run(L) for L in (1, 2, 3)}
res['lag2_rcept_no_date'] = run(2, True)
s1 = E[E.sig == 'S1'].x.values
res['S1_without_largest_event'] = tstat(np.sort(s1)[:-1])
res['S1_largest_event_excess'] = float(s1.max())
res['S1_mean_needed_for_t_2.24_at_observed_sd'] = float(2.24 * s1.std(ddof=1) / np.sqrt(len(s1)))
print(json.dumps(res, indent=1))
json.dump(res, open(OUT, 'w'), indent=1)
