"""PSL1 step 2: walk-forward per-stock lattice (PRECOMMIT_PSL1.md sec. 2-3). Reads feat.npz, writes scores.npz + IC table."""
import sys, json, itertools, numpy as np, pandas as pd
src, out = sys.argv[1], sys.argv[2]
Z = np.load(src)
D, E, F, y, g, gok, mon = Z['D'], Z['E'], Z['F'], Z['y'], Z['g'], Z['gok'], Z['mon']
dates = pd.DatetimeIndex(Z['dates'])
nd, N = E.shape
E = E & gok[:, None]
# terciles per decision among eligible
B = np.full((4, nd, N), -1, np.int8)
for k in range(4):
    x = np.where(E, F[k], np.nan)
    r = pd.DataFrame(x).rank(axis=1, pct=True).values
    B[k] = np.where(np.isfinite(r), np.minimum((r * 3 - 1e-9).astype(int), 2), -1)
G = np.broadcast_to(g[:, None], (nd, N)).astype(np.int16)
subs = []
for k in range(4):
    subs.append((f'{"m r1 v h".split()[k]}', np.where(B[k] >= 0, B[k] * 2 + G, -1), 6))
for a, b in itertools.combinations(range(4), 2):
    nm = "m r1 v h".split()
    subs.append((f'{nm[a]}x{nm[b]}', np.where((B[a] >= 0) & (B[b] >= 0), (B[a] * 3 + B[b]) * 2 + G, -1), 18))
subs.append(('month', np.where(E, np.broadcast_to(mon[:, None] - 1, (nd, N)), -1), 12))
S = len(subs)
yc = np.clip(y, -0.5, 1.0)
hit = (y > 0).astype(np.float64)
st = []
for nm, C, K in subs:
    st.append(dict(n=np.zeros((N, K)), sy=np.zeros((N, K)), sh=np.zeros((N, K)), Pn=np.zeros(K), Py=np.zeros(K),
                   Py2=np.zeros(K), Ph=np.zeros(K), tau=0.0, tauh=0.0))
POOL = np.full((nd, N), np.nan); DEV = np.full((nd, N), np.nan); PP = np.full((nd, N), np.nan); DP = np.full((nd, N), np.nan)
DEVs = np.full((S, nd, N), np.nan)
tau_log = []
cols = np.arange(N)
for j in range(nd):
    jo = j - 2
    if jo >= 0:
        ok = E[jo] & np.isfinite(y[jo])
        for s, (nm, C, K) in enumerate(subs):
            c = C[jo]; m = ok & (c >= 0); ii, cc = cols[m], c[m]; v, h = yc[jo, m], hit[jo, m]
            T = st[s]
            np.add.at(T['n'], (ii, cc), 1.0); np.add.at(T['sy'], (ii, cc), v); np.add.at(T['sh'], (ii, cc), h)
            np.add.at(T['Pn'], cc, 1.0); np.add.at(T['Py'], cc, v); np.add.at(T['Py2'], cc, v * v); np.add.at(T['Ph'], cc, h)
    if not E[j].any():
        continue
    newyear = j == 0 or dates[j].year != dates[j - 1].year
    pool = np.zeros(N); dev = np.zeros(N); pp = np.zeros(N); dp = np.zeros(N)
    for s, (nm, C, K) in enumerate(subs):
        T = st[s]
        Pn = T['Pn']; okc = Pn >= 100
        mu = np.where(okc, T['Py'] / np.maximum(Pn, 1), 0.0)
        var = np.where(okc, T['Py2'] / np.maximum(Pn, 1) - mu ** 2, np.nan)
        ph = np.where(okc, T['Ph'] / np.maximum(Pn, 1), 0.5)
        n = T['n']
        with np.errstate(invalid='ignore', divide='ignore'):
            ybar = T['sy'] / n; hbar = T['sh'] / n
        if newyear:
            q = (n >= 5) & okc[None, :]
            if q.sum() > 50:
                d = (ybar - mu[None, :])[q]; nz = (np.broadcast_to(var[None, :], n.shape) / np.maximum(n, 1))[q]
                T['tau'] = max(0.0, float(np.mean(d * d - nz)))
                dh = (hbar - ph[None, :])[q]; nzh = (np.broadcast_to((ph * (1 - ph))[None, :], n.shape) / np.maximum(n, 1))[q]
                T['tauh'] = max(0.0, float(np.mean(dh * dh - nzh)))
            if s == 0 or True:
                tau_log.append((str(dates[j].date()), nm, T['tau'], T['tauh'], float(np.nanmean(var))))
        c = C[j]; m = E[j] & (c >= 0); ii, cc = cols[m], c[m]
        nn = n[ii, cc]
        lam = np.where(nn > 0, T['tau'] / (T['tau'] + var[cc] / np.maximum(nn, 1)), 0.0) if T['tau'] > 0 else np.zeros(len(ii))
        lamh = np.where(nn > 0, T['tauh'] / (T['tauh'] + ph[cc] * (1 - ph[cc]) / np.maximum(nn, 1)), 0.0) if T['tauh'] > 0 else np.zeros(len(ii))
        lam = np.nan_to_num(lam); lamh = np.nan_to_num(lamh)
        dd = np.where(nn > 0, np.nan_to_num(ybar[ii, cc]) - mu[cc], 0.0)
        ddh = np.where(nn > 0, np.nan_to_num(hbar[ii, cc]) - ph[cc], 0.0)
        pool[ii] += mu[cc]; dev[ii] += lam * dd; pp[ii] += ph[cc]; dp[ii] += lamh * ddh
        DEVs[s, j, ii] = lam * dd
    e = E[j]
    POOL[j, e] = pool[e] / S; DEV[j, e] = dev[e] / S; PP[j, e] = pp[e] / S; DP[j, e] = dp[e] / S
PSL = POOL + DEV; PROB = PP + DP

def ic_series(X):
    out = np.full(nd, np.nan)
    for j in range(nd):
        m = np.isfinite(X[j]) & np.isfinite(y[j])
        if m.sum() > 50 and np.nanstd(X[j][m]) > 0:
            a = pd.Series(X[j][m]).rank().values; b = pd.Series(y[j][m]).rank().values
            out[j] = np.corrcoef(a, b)[0, 1]
    return out

def summ(ic, a, b):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)) & np.isfinite(ic)
    x = ic[m]; n = len(x)
    # Newey-West (lag 3) t
    xm = x - x.mean(); g0 = (xm @ xm) / n; s2 = g0
    for L in range(1, 4):
        s2 += 2 * (1 - L / 4) * (xm[L:] @ xm[:-L]) / n
    return dict(ic=float(x.mean()), t=float(x.mean() / np.sqrt(s2 / n)), n=n, hit=float((x > 0).mean()))

res = {}
mom = np.where(E, F[0], np.nan)
for nm, X in [('POOL', POOL), ('DEV', DEV), ('PSL', PSL), ('PROB', PROB), ('DEVP', DP), ('MOM12_1', mom)]:
    ic = ic_series(X)
    res[nm] = dict(design=summ(ic, '1976-01-01', '1995-12-31'), confirm=summ(ic, '1996-01-01', '2014-12-31'),
                   w86=summ(ic, '1986-01-01', '2014-12-31'))
for s, (nm, C, K) in enumerate(subs):
    ic = ic_series(DEVs[s])
    res['DEV_' + nm] = dict(design=summ(ic, '1976-01-01', '1995-12-31'), confirm=summ(ic, '1996-01-01', '2014-12-31'))
# incremental: partial info of DEV beyond POOL -> IC of PSL minus POOL
for k in ('design', 'confirm', 'w86'):
    res.setdefault('INCR', {})[k] = res['PSL'][k]['ic'] - res['POOL'][k]['ic']
tl = pd.DataFrame(tau_log, columns=['date', 'sub', 'tau2', 'tau2_hit', 'var'])
res['tau_last'] = tl.groupby('sub').last().to_dict('index')
res['tau_frac_pos'] = tl.groupby('sub').apply(lambda d: float((d.tau2 > 0).mean())).to_dict()
np.savez_compressed(out, POOL=POOL.astype(np.float32), DEV=DEV.astype(np.float32), PSL=PSL.astype(np.float32),
                    PROB=PROB.astype(np.float32), DP=DP.astype(np.float32))
json.dump(res, open(out.replace('.npz', '_ic.json'), 'w'), indent=1)
for k, v in res.items():
    if isinstance(v, dict) and 'design' in v:
        print(f"{k:12s} " + ' | '.join(f"{p}: IC {v[p]['ic']:+.4f} t {v[p]['t']:+.2f}" for p in v if isinstance(v[p], dict)))
print('INCR', res['INCR'])
for k, v in res['tau_last'].items():
    print(k, v, 'frac tau>0', res['tau_frac_pos'][k])
