"""NI1 test C: IGREA dry-bulk freight -> CYC/DEF industry score, S&P 500 PIT, monthly rank IC.
Spec: PRECOMMIT_NI1.md section C + spec_choices_C.json (written before returns were computed).
Usage: python -I run_c.py <igrea.csv> <kf17_daily.csv> <panel.npz.xz> <out.json>
"""
import sys, io, json, lzma
import numpy as np, pandas as pd
from scipy.stats import rankdata

IG, KF, PANEL, OUT = sys.argv[1:5]
CUT = 20141231
CYC = ['Mines', 'Steel', 'Machn', 'Chems', 'Trans']
DEF = ['Food', 'Utils', 'Cnsum']

# ---- IGREA (cut at 2014-12) ----
g = pd.read_csv(IG, header=None, names=['date', 'v'])
g = g[pd.to_numeric(g['v'], errors='coerce').notna()]
g['p'] = pd.PeriodIndex(pd.to_datetime(g['date']), freq='M')
g = g.set_index('p')['v'].astype(float)
g = g[g.index <= pd.Period('2014-12', 'M')]
chg3 = g.diff(3)                       # v(k) - v(k-3), indexed by k
sig = chg3.shift(2)                    # decision month m uses k = m-2
med = sig.expanding(24).median()
high = (sig > med).where(med.notna() & sig.notna())

# ---- Ken French 17 industry daily, VW block ----
lines = open(KF).read().splitlines()
s = [i for i, l in enumerate(lines) if 'Average Value Weighted Returns' in l][0]
e = [i for i, l in enumerate(lines) if 'Average Equal Weighted Returns' in l][0]
hdr = [c.strip() for c in lines[s + 1].split(',')]
rows = [l.split(',') for l in lines[s + 2:e] if l.strip() and l.split(',')[0].strip().isdigit()]
kf = pd.DataFrame([[float(x) for x in r[1:]] for r in rows], index=[int(r[0]) for r in rows], columns=hdr[1:])
kf = kf[kf.index <= CUT]
kf = kf.mask(kf <= -99.99) / 100.0
IND = list(kf.columns)
assert len(IND) == 17 and all(c in IND for c in CYC + DEF)

# ---- panel: only dates, adj, member ----
z = np.load(io.BytesIO(lzma.open(PANEL).read()), allow_pickle=False)
dates = pd.to_datetime(z['dates'].astype('datetime64[D]')).strftime('%Y%m%d').astype(int).values; adj = z['adj'].astype(np.float64); T, N = adj.shape
member = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
assert dates.max() <= CUT
valid = np.isfinite(adj) & (adj > 0)
memcum = np.cumsum(member, axis=0) > 0           # on/after first membership day (PIT)
ret = np.full_like(adj, np.nan); ret[1:] = adj[1:] / adj[:-1] - 1
ret[1:][~(valid[1:] & valid[:-1])] = np.nan
okret = np.isfinite(ret) & memcum
okret[1:] &= memcum[:-1]                         # previous row must also be on/after first membership
kfa = kf.reindex(dates)                          # aligned to panel rows
kf_ok = kfa.notna().all(axis=1).values
X_all = kfa.values

dper = pd.PeriodIndex(pd.to_datetime(dates.astype(str), format='%Y%m%d'), freq='M')
mend = np.where(dper[:-1] != dper[1:])[0]        # last row of each month (excluding final row)
mend = np.append(mend, T - 1)

ics, info = [], []
for j in range(len(mend) - 1):
    d = mend[j]; m = dper[d]; end = mend[j + 1]
    if d < 252 or d + 2 > end:
        continue
    h = high.get(m, np.nan)
    if not (h == 0 or h == 1):
        continue
    h = bool(h)
    w = slice(d - 251, d + 1)                    # 252 return rows ending at d
    rw = ret[w]; okw = okret[w]
    full = okw.all(axis=0) & valid[d - 252]      # 253 valid price rows
    elig = full & member[d] & valid[d] & valid[d + 2]
    idx = np.where(elig)[0]
    if len(idx) < 30:
        continue
    kr = kf_ok[w]
    X = np.column_stack([np.ones(kr.sum()), X_all[w][kr]])
    B = np.linalg.lstsq(X, rw[kr][:, idx], rcond=None)[0][1:]   # 17 x n
    ind = np.array(IND)[np.argmax(B, axis=0)]
    sc = np.zeros(len(idx))
    sc[np.isin(ind, CYC)] = 1.0 if h else -1.0
    sc[np.isin(ind, DEF)] = -1.0 if h else 1.0
    # holding return d+2 -> end, with lab delisting value if price missing at end
    p0 = adj[d + 2, idx]
    r = np.empty(len(idx))
    for k, i in enumerate(idx):
        if valid[end, i]:
            r[k] = adj[end, i] / p0[k] - 1
        else:
            vv = np.where(valid[d + 2:end + 1, i])[0]
            last = d + 2 + vv[-1]
            base = last - 250
            r250 = adj[last, i] / adj[base, i] - 1 if base >= 0 and valid[base, i] else np.nan
            dl = -0.5 if (np.isfinite(r250) and r250 < -0.3) else 0.0
            r[k] = (adj[last, i] / p0[k]) * (1 + dl) - 1
    if np.all(sc == sc[0]):
        continue
    ic = np.corrcoef(rankdata(sc), rankdata(r))[0, 1]
    hm = dper[end]
    ics.append((str(hm), ic))
    info.append(dict(hold=str(hm), n=int(len(idx)), n_mem=int((member[d] & valid[d]).sum()),
                     ncyc=int(np.isin(ind, CYC).sum()), ndef=int(np.isin(ind, DEF).sum()), high=h,
                     ndelist=int((~valid[end, idx]).sum()), kfrows=int(kr.sum())))

df = pd.DataFrame(ics, columns=['hold', 'ic']); inf = pd.DataFrame(info)
df['y'] = df['hold'].str[:4].astype(int)

def stats(x):
    x = np.asarray(x, float)
    return dict(n=int(len(x)), mean=float(x.mean()), sd=float(x.std(ddof=1)),
                t=float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))), pos_share=float((x > 0).mean()))

prim = df[(df.y >= 1986) & (df.y <= 2014)]
p1 = df[(df.y >= 1986) & (df.y <= 1999)]; p2 = df[(df.y >= 2000) & (df.y <= 2014)]
allr = df
S = dict(primary_1986_2014=stats(prim.ic), sub_1986_1999=stats(p1.ic), sub_2000_2014=stats(p2.ic),
         all_available=dict(stats(allr.ic), first=allr.hold.iloc[0], last=allr.hold.iloc[-1]),
         by_decade={f"{a}-{a+9}": stats(df[(df.y >= a) & (df.y <= a + 9)].ic)['mean'] for a in (1970, 1980, 1990, 2000, 2010)})
ii = inf[(inf.hold.str[:4].astype(int) >= 1986)]
cov = dict(months_primary=int(len(prim)), avg_stocks=float(ii.n.mean()), min_stocks=int(ii.n.min()),
           avg_share_of_members_scored=float((ii.n / ii.n_mem).mean()),
           avg_cyc=float(ii.ncyc.mean()), avg_def=float(ii.ndef.mean()),
           share_months_high=float(ii.high.mean()), delist_rows=int(ii.ndelist.sum()),
           min_kf_rows=int(inf.kfrows.min()))
# high vs low months IC (descriptive)
mp = prim.merge(inf[['hold', 'high']], on='hold')
S['primary_high_months_mean'] = float(mp[mp.high].ic.mean()); S['primary_low_months_mean'] = float(mp[~mp.high].ic.mean())
keep = (S['primary_1986_2014']['mean'] >= 0.05 and np.sign(S['sub_1986_1999']['mean']) == np.sign(S['sub_2000_2014']['mean'])
        and S['all_available']['mean'] >= 0.05)
S['verdict'] = 'KEEP' if keep else 'CLOSE'
S['coverage'] = cov
S['igrea_last_month_used'] = str(g.index.max()); S['kf_last_date'] = int(kf.index.max()); S['panel_last_date'] = int(dates.max())
json.dump(S, open(OUT, 'w'), indent=1)
print(json.dumps(S, indent=1))
