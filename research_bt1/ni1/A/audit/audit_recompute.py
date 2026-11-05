# NI1-A audit: independent recomputation of S1/S2 event returns (does NOT import the A/code modules).
# Inputs: docs_parsed.jsonl (numbers only) + marcap parquet. Output: printed numbers + json (no names).
import sys, json, bisect
import numpy as np, pandas as pd

DOCS = sys.argv[1]
OUT = sys.argv[2]
EVCSV = sys.argv[3]  # derived per-event table, kept in scratchpad (not in project)
MC = '/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-%d.parquet'
H = 21

cols = ['Code', 'Date', 'Close', 'Changes', 'ChangesRatio', 'Market', 'Stocks']
m = pd.concat([pd.read_parquet(MC % y, columns=cols) for y in range(2002, 2010)], ignore_index=True)
assert m.Date.max() <= pd.Timestamp('2014-12-31')
m['ds'] = m.Date.dt.strftime('%Y%m%d')
# my own daily return from Close/Changes (full precision) and the rounded ChangesRatio
base = m.Close - m.Changes
m['r_cc'] = np.where(base > 0, m.Changes / base, np.nan)
m['r_cr'] = m.ChangesRatio / 100.0
dd = (m.r_cc - m.r_cr).abs()
chk_cc_vs_cr = dict(max_abs_diff=float(dd.max()), share_gt_1e4=float((dd > 1e-4).mean()), n=int(dd.notna().sum()))

days = sorted(m.loc[m.Market == 'KOSPI', 'ds'].unique())
pos = {d: i for i, d in enumerate(days)}
kmask = m.Market == 'KOSPI'
kospi_on = set(zip(m.loc[kmask, 'ds'], m.loc[kmask, 'Code']))
any_on = {(a, b): c for a, b, c in zip(m.ds, m.Code, m.Market)}
codes_ever = set(m.Code)

# wide panels (day x code)
R_cr = m.pivot(index='ds', columns='Code', values='r_cr').reindex(days)
R_cc = m.pivot(index='ds', columns='Code', values='r_cc').reindex(days)
K = m.assign(k=kmask.astype(float)).pivot(index='ds', columns='Code', values='k').reindex(days).fillna(0.0)
# EW benchmark A (as specified/chosen): daily mean of KOSPI ChangesRatio
ew_daily = (R_cr.where(K > 0)).mean(axis=1).values

def last_td_le(d):
    i = bisect.bisect_right(days, d) - 1
    return i

docs = [json.loads(l) for l in open(DOCS)]
cnt = dict(parsed=0, nonzero=0, s1=0, s2=0, nocode=0, not_kospi=0, not_kospi_kosdaq=0, not_kospi_absent_that_day=0,
           not_kospi_code_never_in_marcap=0, not_kospi_absent_but_code_elsewhere=0, nonTD_rcept=0, no_entry_row=0)
not_kospi_by_cls = {}
ev = []
for d in docs:
    if not d.get('parsed'):
        continue
    cnt['parsed'] += 1
    if d['net'] == 0:
        continue
    cnt['nonzero'] += 1
    sig = 'S1' if d['net'] > 0 else 'S2'
    cnt[sig.lower()] += 1
    code = str(d.get('stock_code') or '').strip()
    if not (len(code) == 6):
        cnt['nocode'] += 1; continue
    rd = d['rcept_dt']
    if rd not in pos:
        cnt['nonTD_rcept'] += 1
    i0 = last_td_le(rd)
    dm = days[i0]
    if (dm, code) not in kospi_on:
        cnt['not_kospi'] += 1
        mk = any_on.get((dm, code))
        not_kospi_by_cls[d.get('corp_cls')] = not_kospi_by_cls.get(d.get('corp_cls'), 0) + 1
        if mk == 'KOSDAQ':
            cnt['not_kospi_kosdaq'] += 1
        elif mk is None:
            cnt['not_kospi_absent_that_day'] += 1
            if code in codes_ever:
                cnt['not_kospi_absent_but_code_elsewhere'] += 1
            else:
                cnt['not_kospi_code_never_in_marcap'] += 1
        continue
    # entry = 2nd trading day strictly after rcept_dt
    after = [j for j in range(i0 + 1, min(i0 + 4, len(days))) if days[j] > rd]
    ie = after[1]
    if code not in R_cr.columns or np.isnan(R_cr.at[days[ie], code]):
        cnt['no_entry_row'] += 1; continue
    w = slice(ie + 1, ie + 1 + H)
    assert ie + H < len(days)
    rcr = R_cr[code].values[w]; rcc = R_cc[code].values[w]
    nmiss = int(np.isnan(rcr).sum())
    r_stock = np.prod(1 + np.nan_to_num(rcr)) - 1
    r_stock_cc = np.prod(1 + np.nan_to_num(rcc)) - 1
    r_ew = np.prod(1 + ew_daily[w]) - 1
    # sensitivity: buy-and-hold EW of KOSPI members on entry day (members missing later -> 0 that day)
    memb = K.iloc[ie].values > 0
    sub = np.nan_to_num(R_cr.values[w][:, memb])
    r_bh = np.mean(np.prod(1 + sub, axis=0) - 1)
    # sensitivity: buy-and-hold EW excluding the event stock and preferred shares (code not ending in '0')
    ccols = R_cr.columns.values
    memb2 = memb & np.array([c[-1] == '0' for c in ccols]) & (ccols != code)
    sub2 = np.nan_to_num(R_cr.values[w][:, memb2])
    r_bh2 = np.mean(np.prod(1 + sub2, axis=0) - 1)
    ev.append(dict(sig=sig, rcept_no=d['rcept_no'], rcept_dt=rd, code=code, i0=i0, ie=ie, entry=days[ie],
                   gap_td=ie - i0, r=r_stock, r_cc=r_stock_cc, m=r_ew, m_bh=r_bh, m_bh2=r_bh2, nmiss=nmiss))
E = pd.DataFrame(ev)
E['x'] = E.r - E.m
E['x_cc'] = E.r_cc - E.m
E['x_bh'] = E.r - E.m_bh
E['x_bh2'] = E.r - E.m_bh2


def st(x, grp):
    x = np.asarray(x, float); n = len(x); mu = x.mean(); sd = x.std(ddof=1)
    tn = mu / (sd / np.sqrt(n))
    g = pd.Series(x - mu).groupby(np.asarray(grp)).sum().values; G = len(g)
    tc = mu / (np.sqrt(G / (G - 1) * (g ** 2).sum()) / n)
    return dict(n=n, mean=mu, t_naive=tn, t_cl=tc, t_gate=min(tn, tc))


res = dict(counts=cnt, not_kospi_by_corp_cls_now=not_kospi_by_cls, check_changes_vs_ratio=chk_cc_vs_cr,
           entry_gap_tradingdays_counts=E.gap_td.value_counts().to_dict())
for sig in ('S1', 'S2'):
    X = E[E.sig == sig]
    mon = X.entry.str[:6].values
    o = {}
    for col in ('x', 'x_cc', 'x_bh', 'x_bh2'):
        s = st(X[col], mon)
        p1 = X[X.rcept_dt <= '20051231'][col].mean(); p2 = X[X.rcept_dt >= '20060101'][col].mean()
        s.update(sub1=p1, sub2=p2)
        o[col] = s
    o['dedup_code_rcept_dt'] = st(X.drop_duplicates(['code', 'rcept_dt']).x, X.drop_duplicates(['code', 'rcept_dt']).entry.str[:6])
    o['common_only_x'] = st(X[X.code.str[-1] == '0'].x, X[X.code.str[-1] == '0'].entry.str[:6])
    o['winsor1pct_x'] = st(X.x.clip(X.x.quantile(.01), X.x.quantile(.99)), mon)
    o['events_with_missing_days'] = int((X.nmiss > 0).sum())
    o['mean_r'] = X.r.mean(); o['mean_m'] = X.m.mean(); o['mean_m_bh'] = X.m_bh.mean()
    res[sig] = o
E.drop(columns=['code']).to_csv(EVCSV, index=False)
json.dump(res, open(OUT, 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
