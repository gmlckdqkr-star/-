"""M2 data build (no return statistics are printed here).
Inputs: lab sp500 v3 panel (via lab.stocks, sealed <= 2014-12-31), OAP Predictors.parquet (rows > 201412 dropped on read),
INF1 permno link. Output (scratch): m2data.npz with
  dec (decision rows, lab monthly = first trading row of each month), ddate, elig [nd,N], HR [nd,N] holding return
  exec(D_j+2) -> exec(D_{j+1}+2) under lab H_CONS (classified delisting -50%/0), CR [nd] T-bill over the same span,
  SR [nd,N,S] signed centered cross-sectional rank of each signal among eligible names (NaN = missing),
  up [nd] (_SP500EW > SMA200 at D), moff [nd] (macro inv|csj|shock at D), crash [nd,N] (crash filter flag),
  grp [nd,N] pseudo-sector id (k-means on trailing 252-row returns, refit each January), meta.
OAP timing: decision in calendar month M reads OAP row yyyymm = M-2 (OAP's own lags kept + 1 extra month).
Usage: python3 -B build_data.py <oap_parquet> <link_csv> <signaldoc_csv> <out_npz>"""
import sys, os, json, time, numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks, dsl, data

oap_p, link_p, doc_p, out_p = sys.argv[1:5]
t0 = time.time()
log = lambda *a: print(f'[{time.time() - t0:6.0f}s]', *a, flush=True)
P = stocks.load()
idx = P.idx
assert idx[-1] <= pd.Timestamp('2014-12-31')
T, N = P.T, P.N
Dall = np.flatnonzero(dsl.reb_rows(idx, 'monthly'))
D = Dall[(idx[Dall] >= '1975-01-01')]
nd = len(D)
ddate = idx[D]
log('panel', T, N, 'decisions', nd, ddate[0].date(), ddate[-1].date())
# ---------------- holding returns (lab H_CONS returns), cash
R = P.R(stocks.H_CONS)
LR = np.log1p(np.nan_to_num(R, nan=0.0))
cum = np.vstack([np.zeros((1, N)), np.cumsum(LR, axis=0)])        # cum[t+1] = sum rows <= t
rf = stocks.rf_on(idx)
crf = np.r_[0.0, np.cumsum(np.log1p(rf))]
ex = D + 2
exn = np.r_[D[1:] + 2, T - 1]
exn = np.minimum(exn, T - 1)
HR = (np.exp(cum[exn + 1] - cum[ex + 1]) - 1.0).astype(np.float32)
CR = (np.exp(crf[exn + 1] - crf[ex + 1]) - 1.0)
elig = P.member[D] & P.has[D]
log('HR built; mean eligible', elig.sum(1).mean())
# ---------------- regimes at D
ew = stocks.sp500ew(P)
sma = pd.Series(ew).rolling(200, min_periods=200).mean().values
up = (ew[D] > sma[D]) & np.isfinite(sma[D])
mf = data.macro_flags(idx)
moff = (mf['inv'].values | mf['csj'].values | mf['shock'].values)[D]
log('up share', up.mean().round(3), 'macro-off share', moff.mean().round(3))
# ---------------- crash filter (lab-safe windows from wfloor): ret(21) < -15% or high_dist(252) < -40%
PP = P.P
crash = np.zeros((nd, N), bool)
for j, t in enumerate(D):
    ok21 = (t - 21 >= P.wfloor)
    r21 = np.where(ok21, PP[t] / PP[max(t - 21, 0)] - 1.0, np.nan)
    a = max(t - 251, 0)
    ok252 = (a >= P.wfloor) & (t - 251 >= 0)
    hi = np.nanmax(PP[a:t + 1], axis=0)
    hd = np.where(ok252, PP[t] / hi - 1.0, np.nan)
    crash[j] = (np.nan_to_num(r21, nan=0.0) < -0.15) | (np.nan_to_num(hd, nan=0.0) < -0.40)
log('crash share among eligible', (crash & elig).sum() / elig.sum())
# ---------------- pseudo-sectors: k-means (k=10, seed fixed) on trailing 252-row daily returns, refit each January
rr = P.rr
grp = np.full((nd, N), 10, np.int8)
rng = np.random.default_rng(2014)
cur = None
for j, t in enumerate(D):
    if cur is None or ddate[j].month == 1:
        a = t - 251
        ok = elig[j] & (a >= P.wfloor) & (a >= 0)
        X = rr[a:t + 1][:, ok].T
        X = X - X.mean(1, keepdims=True)
        X = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12)
        C = X[rng.choice(len(X), 10, replace=False)]
        for it in range(30):
            lab_ = np.argmax(X @ C.T, axis=1)
            Cn = np.vstack([X[lab_ == k].mean(0) if (lab_ == k).any() else C[k] for k in range(10)])
            Cn = Cn / np.maximum(np.linalg.norm(Cn, axis=1, keepdims=True), 1e-12)
            if np.allclose(Cn, C):
                break
            C = Cn
        cur = np.full(N, 10, np.int8); cur[np.flatnonzero(ok)] = lab_
        curC = C
    g = cur.copy()
    # names without an assignment (joined after the January fit / short history) stay group 10
    grp[j] = np.where(elig[j], g, 10)
log('groups built; share unassigned among eligible', ((grp == 10) & elig).sum() / elig.sum())
# ---------------- OAP signals
doc = pd.read_csv(doc_p)
doc = doc[doc['Cat.Signal'] == 'Predictor'].set_index('Acronym')
pf = pq.ParquetFile(oap_p)
cols = [c for c in pf.schema_arrow.names if c not in ('permno', 'yyyymm')]
lk = pd.read_csv(link_p)
perms = np.unique(lk.permno.values).astype(np.int32)
pieces = []
for b in pf.iter_batches(batch_size=200_000):
    m = pc.and_(pc.less_equal(b.column('yyyymm'), 201412), pc.greater_equal(b.column('yyyymm'), 197001))
    m = pc.and_(m, pc.is_in(b.column('permno'), value_set=pa.array(perms)))
    bb = b.filter(m)
    if bb.num_rows:
        pieces.append(bb)
tab = pa.Table.from_batches(pieces)
log('OAP rows kept (<=201412, linked permnos)', tab.num_rows)
perm = tab.column('permno').to_numpy().astype(np.int64)
ym = tab.column('yyyymm').to_numpy().astype(np.int64)
assert ym.max() <= 201412
key = perm * 1_000_000 + ym
order = np.argsort(key, kind='stable'); key = key[order]
V = np.empty((len(key), len(cols)), np.float32)
for i, c in enumerate(cols):
    V[:, i] = tab.column(c).to_numpy(zero_copy_only=False).astype(np.float32)[order]
del tab, pieces
# STreversal from the panel (lab-safe): return of calendar month M-2 (same extra lag), sign -1
cols.append('STreversal')
# col -> permno per decision (source month M-2): candidate with an OAP row that month, priority larger n
src = np.array([(d.year * 12 + d.month - 1) - 2 for d in ddate])
src_ym = (src // 12) * 100 + (src % 12) + 1
cand = {}
for c_, g in lk.sort_values('n', ascending=False).groupby('col'):
    cand[int(c_)] = g.permno.values.astype(np.int64)
rowix = np.full((nd, N), -1, np.int64)
for j in range(nd):
    for c_, pl in cand.items():
        for p_ in pl:
            k = p_ * 1_000_000 + src_ym[j]
            i = np.searchsorted(key, k)
            if i < len(key) and key[i] == k:
                rowix[j, c_] = i
                break
log('linked & eligible share', ((rowix >= 0) & elig).sum() / elig.sum())
S = len(cols)
sign = np.array([float(doc.loc[c, 'Sign']) if c in doc.index else -1.0 for c in cols])
SR = np.full((nd, N, S), np.nan, np.float32)
for s in range(S - 1):
    X = np.where(rowix >= 0, V[np.maximum(rowix, 0), s], np.nan) * sign[s]
    X[~elig] = np.nan
    Rk = pd.DataFrame(X).rank(axis=1, method='average')
    n = Rk.notna().sum(1).values[:, None]
    SR[:, :, s] = ((Rk.values - 0.5) / np.maximum(n, 1) - 0.5).astype(np.float32)
# STreversal
st = np.full((nd, N), np.nan)
for j, t in enumerate(D):
    jj = np.searchsorted(Dall, t)
    if jj >= 3:
        a, b = Dall[jj - 2] - 1, Dall[jj - 1] - 1          # last row of month M-3, last row of month M-2
        ok = (a >= P.wfloor)
        st[j] = np.where(ok, PP[b] / PP[a] - 1.0, np.nan)
X = st * sign[-1]; X[~elig] = np.nan
Rk = pd.DataFrame(X).rank(axis=1, method='average'); n = Rk.notna().sum(1).values[:, None]
SR[:, :, -1] = ((Rk.values - 0.5) / np.maximum(n, 1) - 0.5).astype(np.float32)
log('SR built', SR.shape)
year = np.array([float(doc.loc[c, 'Year']) if c in doc.index else 1990.0 for c in cols])
econ = [str(doc.loc[c, 'Cat.Economic']) if c in doc.index else 'short-term reversal' for c in cols]
datac = [str(doc.loc[c, 'Cat.Data']) if c in doc.index else 'Price' for c in cols]
pq_ = [str(doc.loc[c, 'Predictability in OP']) if c in doc.index else '1_clear' for c in cols]
tst = np.array([float(doc.loc[c, 'T-Stat']) if c in doc.index and pd.notna(doc.loc[c, 'T-Stat']) else np.nan for c in cols])
np.savez(out_p, dec=D, ddate=ddate.values.astype('datetime64[D]').astype(np.int64), elig=elig, HR=HR, CR=CR, SR=SR,
         up=up, moff=moff, crash=crash, grp=grp, linked=(rowix >= 0), cols=np.array(cols), sign=sign, year=year,
         econ=np.array(econ), datac=np.array(datac), pq=np.array(pq_), tstat=tst)
log('saved', out_p)
