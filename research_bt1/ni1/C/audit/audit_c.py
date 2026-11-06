"""Independent audit of NI1 test C (PRECOMMIT_NI1.md section C). Does not import run_c.py.
Usage: python -I audit_c.py <igrea.xlsx> <kf17_daily.csv> <panel.npz.xz> <out.json>
Reads only dates, adj, member from the panel. IGREA read from the Dallas Fed xlsx directly (not the csv).
Main = spec as pre-registered (implementer's conservative timing, recomputed independently).
Sensitivity rows (labelled, NOT trials, cannot change the verdict) test whether spec ambiguity could flip it.
"""
import sys, io, json, lzma
import numpy as np, pandas as pd
from scipy.stats import spearmanr

IGX, KFP, PAN, OUT = sys.argv[1:5]
CYC = {'Mines', 'Steel', 'Machn', 'Chems', 'Trans'}
DEF = {'Food', 'Utils', 'Cnsum'}

# IGREA from xlsx, cut 2014-12
x = pd.read_excel(IGX, header=None).iloc[1:]
x = x[pd.to_numeric(x[1], errors='coerce').notna()]
gi = pd.Series(x[1].astype(float).values, index=pd.to_datetime(x[0]).dt.to_period('M'))
gi = gi[gi.index <= pd.Period('2014-12', 'M')]
assert gi.index.is_monotonic_increasing and not gi.index.duplicated().any()
mon = pd.period_range(gi.index[0], gi.index[-1], freq='M'); assert len(mon) == len(gi)

def high_series(lag):
    # signal for decision month m = g(m-lag) - g(m-lag-3); high = > expanding median incl. m, >=24 values
    s = {}
    for m in mon:
        a, b = m - lag, m - lag - 3
        if a in gi.index and b in gi.index:
            s[m] = gi[a] - gi[b]
    s = pd.Series(s)
    out = {}
    vals = []
    for m, v in s.items():
        vals.append(v)
        if len(vals) >= 24:
            out[m] = bool(v > np.median(vals))
    return out

# KF 17 VW daily
L = open(KFP).read().splitlines()
i0 = next(i for i, l in enumerate(L) if 'Average Value Weighted Returns -- Daily' in l)
i1 = next(i for i, l in enumerate(L) if 'Average Equal Weighted Returns -- Daily' in l)
cols = [c.strip() for c in L[i0 + 1].split(',')][1:]
rec = {}
for l in L[i0 + 2:i1]:
    p = [q.strip() for q in l.split(',')]
    if len(p) == 18 and p[0].isdigit() and int(p[0]) <= 20141231:
        v = np.array([float(q) for q in p[1:]])
        v[v <= -99.99] = np.nan
        rec[int(p[0])] = v / 100
kf = pd.DataFrame.from_dict(rec, orient='index', columns=cols).sort_index()

# panel
z = np.load(io.BytesIO(lzma.open(PAN).read()))
dt = pd.to_datetime(z['dates'], unit='D')
adj = z['adj'].astype(float); T, N = adj.shape
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
assert dt.max() <= pd.Timestamp('2014-12-31')
ok = np.isfinite(adj) & (adj > 0)
first_mem = np.where(mem.any(0), mem.argmax(0), T + 1)          # first membership row per stock
rowi = np.arange(T)[:, None]
okpit = ok & (rowi >= first_mem[None, :])                       # price usable (on/after first membership)
ymd = dt.strftime('%Y%m%d').astype(int)
KF = kf.reindex(ymd).values
per = dt.to_period('M')
last_rows = [np.where(per == p)[0][-1] for p in per.unique()]
pm = list(per.unique())

def run(lag, verbose=False):
    H = high_series(lag)
    res, cov = [], []
    for j in range(len(pm) - 1):
        m = pm[j]; d = last_rows[j]; end = last_rows[j + 1]; e = d + 2
        if m not in H or d - 252 < 0 or e > end:
            continue
        h = H[m]
        w0 = d - 252                                             # 253 price rows w0..d
        good = okpit[w0:d + 1].all(0) & mem[d] & ok[d] & ok[e]
        ids = np.where(good)[0]
        if len(ids) < 30:
            continue
        P = adj[w0:d + 1][:, ids]
        R = P[1:] / P[:-1] - 1                                   # 252 returns ending at d
        Xk = KF[w0 + 1:d + 1]
        kk = np.isfinite(Xk).all(1)
        X = np.c_[np.ones(kk.sum()), Xk[kk]]
        beta = np.linalg.lstsq(X, R[kk], rcond=None)[0][1:]
        ind = np.array(cols)[beta.argmax(0)]
        c = np.isin(ind, list(CYC)); df_ = np.isin(ind, list(DEF))
        sc = np.where(c, 1.0, 0.0) - np.where(df_, 1.0, 0.0)
        if not h:
            sc = -sc
        r = np.empty(len(ids)); nd = 0
        for k, i in enumerate(ids):
            if ok[end, i]:
                r[k] = adj[end, i] / adj[e, i] - 1
            else:
                nd += 1
                lastv = e + np.where(ok[e:end + 1, i])[0].max()
                b = lastv - 250
                r250 = adj[lastv, i] / adj[b, i] - 1 if (b >= 0 and ok[b, i]) else np.nan
                r[k] = adj[lastv, i] / adj[e, i] * (0.5 if (np.isfinite(r250) and r250 < -0.3) else 1.0) - 1
        if np.ptp(sc) == 0:
            continue
        ic = spearmanr(sc, r).correlation
        res.append((pm[j + 1], ic, h))
        if verbose:
            cov.append(dict(n=len(ids), nmem=int((mem[d] & ok[d]).sum()), ncyc=int(c.sum()), ndef=int(df_.sum()),
                            nd=nd, inds=pd.Series(ind).value_counts().to_dict(), hold=str(pm[j + 1]),
                            exec_after_month_end=bool(per[e] != m), end_is_m1=bool(per[end] == pm[j + 1])))
    df = pd.DataFrame(res, columns=['hold', 'ic', 'high'])
    df['y'] = df.hold.apply(lambda p: p.year)
    return df, cov

def st(s):
    s = np.asarray(s, float)
    return dict(n=len(s), mean=round(float(s.mean()), 5), t=round(float(s.mean() / s.std(ddof=1) * np.sqrt(len(s))), 3))

out = {}
for name, lag in (('main_lag2_decision_end_m', 2), ('sens_lag1_tighter', 1)):
    df, cov = run(lag, verbose=(lag == 2))
    A = df[(df.y >= 1986) & (df.y <= 2014)]; a1 = df[(df.y >= 1986) & (df.y <= 1999)]; a2 = df[(df.y >= 2000) & (df.y <= 2014)]
    o = dict(primary=st(A.ic), p1=st(a1.ic), p2=st(a2.ic), all=st(df.ic), first=str(df.hold.iloc[0]), last=str(df.hold.iloc[-1]),
             high_share_primary=round(float(A.high.mean()), 4),
             gate_keep=bool(st(A.ic)['mean'] >= .05 and np.sign(a1.ic.mean()) == np.sign(a2.ic.mean())))
    if cov:
        cv = pd.DataFrame(cov); cv = cv[cv.hold.str[:4].astype(int) >= 1986]
        tot = {}
        for dct in cv.inds:
            for k, v in dct.items():
                tot[k] = tot.get(k, 0) + v
        sm = sum(tot.values())
        o['coverage'] = dict(avg_n=round(cv.n.mean(), 1), min_n=int(cv.n.min()), share_scored=round(float((cv.n / cv.nmem).mean()), 4),
                             avg_cyc=round(cv.ncyc.mean(), 1), avg_def=round(cv.ndef.mean(), 1), delist_rows=int(cv.nd.sum()),
                             exec_always_in_m1=bool(cv.exec_after_month_end.all()), end_always_m1=bool(cv.end_is_m1.all()),
                             industry_share={k: round(v / sm, 4) for k, v in sorted(tot.items(), key=lambda t: -t[1])})
    out[name] = o
json.dump(out, open(OUT, 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
