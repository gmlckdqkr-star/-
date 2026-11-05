# NI1-A step 3: event returns and stage-1 gate (PRECOMMIT_NI1.md section A; choices in results/A_spec_choices.json).
import os, sys, json
import numpy as np, pandas as pd

RUN, RES = sys.argv[1], sys.argv[2]
MC = '/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-%d.parquet'
H = 21

docs = [json.loads(l) for l in open(os.path.join(RUN, 'docs_parsed.jsonl'))]
mk = pd.concat([pd.read_parquet(MC % y, columns=['Code', 'Date', 'ChangesRatio', 'Market']) for y in range(2002, 2010)])
mk = mk[mk.Date <= '2014-12-31']
kos = mk[mk.Market == 'KOSPI']
days = np.sort(pd.to_datetime(kos.Date.unique()).to_numpy().astype('datetime64[ns]'))
ew = kos.groupby('Date').ChangesRatio.mean().reindex(days) / 100.0
ew_v = ew.values
kos_set = set(zip(kos.Date.values, kos.Code.values))
ret = {c: g.set_index('Date').ChangesRatio / 100.0 for c, g in mk.groupby('Code')}

cnt = dict(docs=len(docs), fetched_ok=0, parsed=0, nonzero_net=0, s1_docs=0, s2_docs=0,
           no_stock_code=0, not_kospi_on_rcept=0, no_row_on_entry=0, window_beyond_data=0)
ev = []
for d in docs:
    if d.get('status') == 'ok':
        cnt['fetched_ok'] += 1
    if not d.get('parsed'):
        continue
    cnt['parsed'] += 1
    net = d['net']
    if net == 0:
        continue
    cnt['nonzero_net'] += 1
    sig = 'S1' if net > 0 else 'S2'
    cnt[sig.lower() + '_docs'] += 1
    code = (d['stock_code'] or '').strip()
    if len(code) != 6:
        cnt['no_stock_code'] += 1; continue
    rd = np.datetime64(pd.Timestamp(d['rcept_dt']))
    j0 = np.searchsorted(days, rd, side='right') - 1       # last trading day <= rcept_dt
    if j0 < 0 or (days[j0], code) not in kos_set:
        cnt['not_kospi_on_rcept'] += 1; continue
    jr = np.searchsorted(days, rd, side='right')            # first trading day > rcept_dt
    je = jr + 1                                             # 2nd trading day after rcept_dt
    if je + H >= len(days):
        cnt['window_beyond_data'] += 1; continue
    s = ret.get(code)
    if s is None or days[je] not in s.index:
        cnt['no_row_on_entry'] += 1; continue
    w = days[je + 1: je + 1 + H]
    rs = s.reindex(w).fillna(0.0).values                    # halt / delisted -> 0
    r_stock = np.prod(1 + rs) - 1
    r_ew = np.prod(1 + ew_v[je + 1: je + 1 + H]) - 1
    ev.append(dict(sig=sig, rcept_dt=d['rcept_dt'], entry=str(days[je])[:10], code=code,
                   r=r_stock, m=r_ew, x=r_stock - r_ew, missing_days=int(pd.isna(s.reindex(w)).sum())))
E = pd.DataFrame(ev)


def stats(x, month):
    x = np.asarray(x, float); n = len(x)
    if n < 3:
        return dict(n=n)
    mu = x.mean(); sd = x.std(ddof=1)
    t_naive = mu / (sd / np.sqrt(n))
    e = x - mu
    g = pd.Series(e).groupby(np.asarray(month)).sum().values
    G = len(g)
    se_cl = np.sqrt(G / (G - 1) * np.sum(g ** 2)) / n
    t_cl = mu / se_cl
    return dict(n=n, mean=mu, median=float(np.median(x)), sd=sd, t_naive=t_naive, t_cluster_month=t_cl,
                n_months=G, t_gate=min(t_naive, t_cl), hit=float((x > 0).mean()))


out = dict(counts=cnt)
for sig in ('S1', 'S2'):
    X = E[E.sig == sig]
    mon = X.entry.str[:7].values
    st = stats(X.x, mon)
    p1 = X[(X.rcept_dt >= '20020701') & (X.rcept_dt <= '20051231')]
    p2 = X[(X.rcept_dt >= '20060101') & (X.rcept_dt <= '20081231')]
    st['sub_2002_07_2005_12'] = dict(n=len(p1), mean=float(p1.x.mean()) if len(p1) else None)
    st['sub_2006_01_2008_12'] = dict(n=len(p2), mean=float(p2.x.mean()) if len(p2) else None)
    st['mean_stock_21d'] = float(X.r.mean()); st['mean_ew_21d'] = float(X.m.mean())
    st['events_with_missing_days'] = int((X.missing_days > 0).sum())
    st['unique_stock_rcept_dt'] = int(X[['code', 'rcept_dt']].drop_duplicates().shape[0])
    st['by_year_mean'] = {k: [int(len(v)), float(v.mean())] for k, v in X.groupby(X.rcept_dt.str[:4]).x}
    out[sig] = st

s1 = out['S1']
reasons = []
if s1['mean'] < 0.010: reasons.append('mean excess < +1.0%')
if s1['t_gate'] < 2.24: reasons.append('t < 2.24')
if s1['sub_2002_07_2005_12']['mean'] < 0: reasons.append('2002-07..2005-12 mean negative')
if s1['sub_2006_01_2008_12']['mean'] < 0: reasons.append('2006-01..2008-12 mean negative')
out['stage1'] = dict(verdict='CLOSE' if reasons else 'PASS_STAGE1', close_reasons=reasons,
                     rule='close if S1 mean<+1.0% or t<2.24 or either sub-period mean<0')
out['benchmark_check'] = dict(n_days=int(len(days)), first=str(days[0])[:10], last=str(days[-1])[:10],
                              ew_daily_mean=float(ew.mean()))
json.dump(out, open(os.path.join(RES, 'A_stage1.json'), 'w'), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
