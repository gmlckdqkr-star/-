# NI1-B independent audit: recompute the Frazzini-Lamont expected-announcer monthly Spearman IC from raw inputs.
# Written from the pre-registration text, not importing the implementer's modules.
# Usage: python -I audit_fl.py <oap_parquet> <out_json>
import sys, io, lzma, json
import numpy as np, pandas as pd
from scipy.stats import spearmanr

OAP, OUT = sys.argv[1], sys.argv[2]
PANEL = '/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz'
LINK = '/mnt/project-files/research/influence/results/link_permno_col.csv'

z = np.load(io.BytesIO(lzma.open(PANEL).read()))
d = z['dates']
dates = pd.to_datetime(d, unit='D') if d.max() < 10**6 else pd.to_datetime(d)
adj = z['adj'].astype(float)
T, N = adj.shape
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
assert dates[-1] <= pd.Timestamp('2014-12-31')
mid = (dates.year * 12 + dates.month - 1).to_numpy()            # absolute month id
mend = np.flatnonzero(np.r_[mid[1:] != mid[:-1], True])          # last trading day per month
mids = mid[mend]; pos = {m: i for i, m in enumerate(mids)}
K = len(mids)

# ---- OAP announcement months
o = pd.read_parquet(OAP)
o = o[o.yyyymm <= 201412].copy()
dup = int(o.duplicated(['permno', 'yyyymm']).sum())
o['mid'] = (o.yyyymm // 100) * 12 + (o.yyyymm % 100) - 1
o = o.sort_values(['permno', 'mid'])
first_row = o.groupby('permno').mid.min()
nn = o[o.AnnouncementReturn.notna()].copy()
nn['prev'] = nn.groupby('permno').AnnouncementReturn.shift(1)
nn['first'] = nn.prev.isna() & ~nn.duplicated('permno')            # first non-null row of the permno
nn['ann'] = (nn.AnnouncementReturn != nn.prev) & nn.prev.notna()
# first non-null counts only if the permno had an earlier (null-AR) row
nn.loc[nn['first'], 'ann'] = nn.loc[nn['first'], 'mid'].values > first_row.loc[nn.loc[nn['first'], 'permno']].values
nn_alt_first = nn.copy(); nn_alt_first.loc[nn_alt_first['first'], 'ann'] = True   # sensitivity: first non-null always counts
perms = np.sort(o.permno.unique()); pj = {p: i for i, p in enumerate(perms)}

def mat(df):
    A = np.zeros((K, len(perms)), bool)
    df = df[df.mid.isin(pos)]
    A[df.mid.map(pos).values, df.permno.map(pj).values] = True
    return A
Iann = mat(nn[nn.ann]); Iann_alt = mat(nn_alt_first[nn_alt_first.ann]); Rrow = mat(o)

# ---- link: (col, month) valid when exactly one of col's permnos has an OAP row that month
lk = pd.read_csv(LINK)
Lmap = np.full((K, N), -1)
for c, g in lk.groupby('col'):
    js = [pj[p] for p in g.permno.unique() if p in pj]
    if not js: continue
    pres = Rrow[:, js]
    ok = pres.sum(1) == 1
    Lmap[ok, c] = np.array(js)[pres[ok].argmax(1)]
memE = mem[mend]
Lmap[~memE] = -1
for k in range(K):
    v = Lmap[k]; u, cnt = np.unique(v[v >= 0], return_counts=True)
    if (cnt > 1).any(): Lmap[k, np.isin(v, u[cnt > 1])] = -1

# ---- shift vote (2008-2014 only), market-adjusted monthly returns
P = adj[mend]
r = np.full_like(P, np.nan); r[1:] = P[1:] / P[:-1] - 1
mkt = np.array([np.nanmean(np.where(memE[k - 1], r[k], np.nan)) if k else np.nan for k in range(K)])
mar = r - mkt[:, None]
v0 = v1 = 0
for k in range(pos[2008 * 12], pos[2014 * 12 + 11] + 1):
    for c in np.flatnonzero(Lmap[k - 2] >= 0):
        j = Lmap[k - 2, c]
        if Iann[k, j] and np.isfinite(mar[k, c]) and np.isfinite(mar[k - 1, c]):
            if abs(mar[k, c]) > abs(mar[k - 1, c]): v0 += 1
            else: v1 += 1
shift = 0 if v0 >= v1 else -1

# ---- IC
def run(I, sh, restrict=False, delist='last'):
    Ip = I if sh == 0 else np.r_[I[1:], np.zeros((1, I.shape[1]), bool)]
    out = []
    for k in range(pos[1974 * 12 + 11], pos[2014 * 12 + 10] + 1):
        cols = np.flatnonzero(Lmap[k] >= 0); js = Lmap[k, cols]
        e0 = mend[k] + 2; e1 = mend[k + 1]
        p0 = adj[e0, cols]
        win = adj[e0:e1 + 1, cols]
        # last finite price in [entry, exit]
        idx = np.where(np.isfinite(win), np.arange(win.shape[0])[:, None], -1).max(0)
        p1 = win[np.maximum(idx, 0), np.arange(len(cols))]
        fr = p1 / p0 - 1
        fr[idx <= 0] = np.nan if delist == 'last' else fr[idx <= 0]
        h = Ip[k - 11:k + 1, js]
        sig = h[0] & ~h[-1] & (h.sum(0) == 4)
        ok = np.isfinite(fr) & np.isfinite(p0)
        if restrict: ok &= h[0]
        s, f = sig[ok], fr[ok]
        ic = spearmanr(s.astype(float), f)[0] if (len(f) >= 20 and 0 < s.sum() < len(s)) else np.nan
        out.append((mids[k + 1] // 12, ic, len(f), int(s.sum())))
    df = pd.DataFrame(out, columns=['y', 'ic', 'n', 'ns'])
    def st(a, b):
        x = df.ic[(df.y >= a) & (df.y <= b)].dropna()
        return dict(mean=round(float(x.mean()), 5), t=round(float(x.mean() / x.std(ddof=1) * len(x) ** .5), 2), n=int(len(x)))
    res = {p: st(a, b) for p, (a, b) in {'1975-2014': (1975, 2014), '1975-84': (1975, 1984), '1985-94': (1985, 1994),
                                         '1995-04': (1995, 2004), '2005-14': (2005, 2014), '1989-2014': (1989, 2014)}.items()}
    res['n_mean'] = round(float(df.n.mean()), 1); res['sig_share'] = round(float((df.ns / df.n).mean()), 4)
    dec = all(res[p]['mean'] > 0 for p in ['1975-84', '1985-94', '1995-04', '2005-14'])
    res['verdict'] = 'KEEP' if (res['1975-2014']['mean'] >= .05 and dec and res['1989-2014']['mean'] > 0) else 'CLOSE'
    return res

res = dict(oap_dup_rows=dup, oap_rows=int(len(o)), oap_max_yyyymm=int(o.yyyymm.max()),
           panel_last=str(dates[-1].date()), shift_votes=dict(v0=v0, v1=v1, share0=round(v0 / (v0 + v1), 4), shift=shift),
           headline=run(Iann, shift),
           sens_nongate=dict(shift_minus1=run(Iann, -1), restrict_to_announced_t_minus_11=run(Iann, shift, restrict=True),
                             first_nonnull_counts=run(Iann_alt, shift)))
json.dump(res, open(OUT, 'w'), indent=1); print(json.dumps(res, indent=1))
