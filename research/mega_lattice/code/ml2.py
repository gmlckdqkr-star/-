"""ML2 (PRECOMMIT_ML2.md): pooled lattice over anomaly long legs, post-publication only. <=2014. usage: python3 ml2.py real | null k"""
import sys, json, itertools, numpy as np, pandas as pd, numba as nb
from scipy.stats import rankdata
ICOST = 0.003
END = pd.Timestamp('2014-12-31'); KAPPA = 300.0
D = '/mnt/project-files/research/data/oap/'
OUT = '/mnt/project-files/research/mega_lattice/results/'


def load():
    a = pd.read_parquet(D + 'PredictorAltPorts_LiqScreen_ME_gt_NYSE20pct.parquet')
    a['date'] = pd.to_datetime(a['date']) + pd.offsets.MonthEnd(0)
    a = a[a['date'] <= END]
    doc = pd.read_csv(D + 'SignalDoc.csv').set_index('Acronym')
    R = a.pivot_table(index='date', columns=['signalname', 'port'], values='ret') / 100
    N = a.pivot_table(index='date', columns=['signalname', 'port'], values='Nlong')
    legs, ls, nl, info = {}, {}, {}, {}
    for s in sorted(a['signalname'].unique()):
        ports = sorted([p for p in R[s].columns if p != 'LS'])
        if 'LS' not in R[s].columns or len(ports) < 2 or s not in doc.index:
            continue
        hi, lo = R[s][ports[-1]], R[s][ports[0]]
        L = R[s]['LS']; m = L.notna() & hi.notna() & lo.notna()
        c = np.corrcoef(L[m], (hi - lo)[m])[0, 1] if m.sum() > 24 else np.nan
        leg = ports[-1] if c > 0 else ports[0]
        legs[s] = R[s][leg]; ls[s] = L; nl[s] = N[s][leg] if leg in N[s].columns else np.nan
        info[s] = dict(leg=leg, corr=float(c), year=int(doc.loc[s, 'Year']), sign=float(doc.loc[s, 'Sign']))
    legs, ls, nl = pd.DataFrame(legs), pd.DataFrame(ls), pd.DataFrame(nl)
    spx = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/SPX_TR_daily_1927_2014.csv', parse_dates=['date']).set_index('date')['tr_index']
    mkt = spx.resample('ME').last().pct_change()
    tb = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/TBILL_daily_1927_2014.csv', parse_dates=['date']).set_index('date')['rate_known_pct']
    rf = (tb / 100 / 12).resample('ME').last().shift(1)          # rate known at start of month
    idx = legs.index
    return legs, ls, nl, mkt.reindex(idx), rf.reindex(idx).fillna(0), info


NF = 12


def features(legs, ls, nl, mkt, info):
    ex = legs.sub(mkt, axis=0)
    lex = np.log1p(legs).sub(np.log1p(mkt), axis=0)
    F = {}
    for n in (1, 3, 6, 12, 36):
        F['ex%d' % n] = lex.rolling(n, min_periods=n).sum()
    F['ls12'] = np.log1p(ls).rolling(12, min_periods=12).sum()
    F['vol12'] = legs.rolling(12, min_periods=12).std()
    mm = mkt.rolling(36, min_periods=36)
    F['beta36'] = pd.DataFrame({s: legs[s].rolling(36, min_periods=36).cov(mkt) / mm.var() for s in legs.columns})
    elig_start = {s: pd.Timestamp(info[s]['year'] + 1, 1, 31) for s in legs.columns}
    months = np.array([(legs.index.year - elig_start[s].year) * 12 + legs.index.month - 1 for s in legs.columns]).T
    F['age'] = pd.DataFrame(months, index=legs.index, columns=legs.columns).astype(float)
    F['mret12'] = pd.DataFrame({s: np.log1p(mkt).rolling(12).sum() for s in legs.columns})
    F['mvol12'] = pd.DataFrame({s: mkt.rolling(12).std() for s in legs.columns})
    F['nlong'] = nl.reindex(columns=legs.columns)
    names = ['ex1', 'ex3', 'ex6', 'ex12', 'ex36', 'ls12', 'vol12', 'beta36', 'age', 'mret12', 'mvol12', 'nlong']
    X = np.stack([F[k].values for k in names], axis=2)        # T x A x 12
    y = ex.shift(-1).values                                    # next-month leg - market
    elig = (F['age'].values >= 0)
    return X, y, elig, names


def subl():
    s = [(i, -1, -1) for i in range(NF)] + [(i, j, -1) for i, j in itertools.combinations(range(NF), 2)] + \
        list(itertools.combinations(range(NF), 3))
    s = np.array(s, np.int64); size = np.where(s[:, 2] >= 0, 125, np.where(s[:, 1] >= 0, 25, 5))
    return s, np.r_[0, np.cumsum(size)[:-1]].astype(np.int64), int(size.sum())


@nb.njit(cache=True)
def _cells(B, subs, off):
    n = B.shape[0]; S = subs.shape[0]; C = np.empty((n, S), np.int64)
    for i in range(n):
        for s in range(S):
            c = off[s] + B[i, subs[s, 0]]
            if subs[s, 1] >= 0:
                c += 5 * B[i, subs[s, 1]]
            if subs[s, 2] >= 0:
                c += 25 * B[i, subs[s, 2]]
            C[i, s] = c
    return C


def run(shift=0):
    legs, ls, nl, mkt, rf, info = load()
    X, y, elig, names = features(legs, ls, nl, mkt, info)
    if shift:
        X = np.roll(X, shift, axis=0)
    T, A, _ = X.shape; dates = legs.index
    subs, off, ncell = subl()
    fold = ((dates.year.values // 5) % 2)
    ok = elig & ~np.isnan(X).any(2)
    MU = np.full((T, A), np.nan); PP = MU.copy()
    for Y in range(1986, 2015):
        tr = ok & ~np.isnan(y) & (dates < pd.Timestamp(Y - 1, 12, 31))[:, None]   # label month <= Dec Y-1
        te = ok & (dates.year.values == Y)[:, None]
        ti, ai = np.where(tr); qi, qa = np.where(te)
        Xtr = X[ti, ai]; edges = [np.unique(np.nanquantile(Xtr[:, j], [.2, .4, .6, .8])) for j in range(NF)]
        def binz(Z):
            return np.stack([np.searchsorted(edges[j], Z[:, j], side='right') for j in range(NF)], 1).astype(np.int64)
        Ctr = _cells(binz(Xtr), subs, off); Cte = _cells(binz(X[qi, qa]), subs, off)
        ytr = y[ti, ai]; utr = (ytr > 0).astype(float); ftr = fold[ti]
        dl = []
        for g in (0, 1):
            m = ftr == g; yb = ytr[m].mean()
            sy = np.bincount(Ctr[m].ravel(), np.repeat(ytr[m], Ctr.shape[1]), minlength=ncell)
            nn = np.bincount(Ctr[m].ravel(), minlength=ncell).astype(float)
            dl.append((sy - nn * yb) / (nn + KAPPA))
        oof = np.where(ftr == 0, dl[1][Ctr].mean(1), dl[0][Ctr].mean(1))
        b, a = np.polyfit(oof, ytr, 1)
        w = logit(oof, utr)
        s_te = (dl[0][Cte].mean(1) + dl[1][Cte].mean(1)) / 2
        MU[qi, qa] = a + b * s_te; PP[qi, qa] = 1 / (1 + np.exp(-(w[0] + w[1] * s_te)))
    return dict(MU=MU, P=PP, y=y, ok=ok, X=X, names=names, dates=dates, legs=legs, mkt=mkt, rf=rf, cols=list(legs.columns))


def logit(x, u, it=25):
    Z = np.c_[np.ones_like(x), x]; w = np.zeros(2)
    for _ in range(it):
        p = 1 / (1 + np.exp(-Z @ w)); W = p * (1 - p)
        w = w + np.linalg.solve(Z.T @ (Z * W[:, None]) + 1e-9 * np.eye(2), Z.T @ (u - p))
    return w


def evaluate(r):
    MU, y, P, dates = r['MU'], r['y'], r['P'], r['dates']
    legs = r['legs'].values; mkt = r['mkt'].values; rf = r['rf'].values
    ex12 = r['X'][:, :, r['names'].index('ex12')]
    ics, icm, nas = [], [], []
    for t in range(len(dates)):
        m = ~np.isnan(MU[t]) & ~np.isnan(y[t])
        if m.sum() >= 10:
            ics.append(np.corrcoef(rankdata(MU[t][m]), rankdata(y[t][m]))[0, 1])
            icm.append(np.corrcoef(rankdata(ex12[t][m]), rankdata(y[t][m]))[0, 1]); nas.append(m.sum())
    st = lambda v: dict(mean=float(np.mean(v)), t=float(np.mean(v) / np.std(v) * len(v) ** .5), n=len(v))
    out = dict(ic=st(ics), ic_factor_mom=st(icm), n_assets_median=float(np.median(nas)))

    def bt(kind):
        prev = None; rets = []; ds = []
        for t in range(len(dates) - 1):
            m = ~np.isnan(MU[t]) & ~np.isnan(legs[t + 1])
            if dates[t].year < 1986 or m.sum() < 10:
                continue
            w = np.zeros(legs.shape[1]); wm = 0.0
            if kind == 'W1':
                top = np.argsort(np.where(m, MU[t], -np.inf))[::-1][:5]; w[top] = 0.2
            elif kind == 'C1':
                sc = np.where(m & ~np.isnan(ex12[t]), ex12[t], -np.inf); top = np.argsort(sc)[::-1][:5]; w[top] = 0.2
            elif kind == 'C0':
                w[m] = 1.0 / m.sum()
            elif kind == 'W2':
                sc = np.where(m, P[t], -np.inf); top = np.argsort(sc)[::-1][:10]
                e = np.clip(P[t][top] - 0.5, 0, None)
                if e.sum() > 0:
                    w[top] = e / e.sum()
                else:
                    wm = 1.0
            r_ = np.nansum(w * legs[t + 1]) + wm * mkt[t + 1]
            cost = 0.003 * (np.abs(w - prev).sum() if prev is not None else 1.0) + ICOST * w.sum()
            prev = w
            rets.append(np.log1p(r_ - cost) - np.log1p(rf[t + 1])); ds.append(dates[t + 1])
        r_ = np.array(rets)
        return dict(sharpe=float(r_.mean() / r_.std() * 12 ** .5), cagr_ex=float(np.expm1(r_.mean() * 12)),
                    cagr_tot=float(np.expm1((r_ + np.log1p(rf[[dates.get_loc(d) for d in ds]])).mean() * 12)), n=len(r_))
    for k in ('W1', 'W2', 'C0', 'C1'):
        out[k] = bt(k)
    mk = np.log1p(mkt[(dates.year >= 1986)]) - np.log1p(rf[(dates.year >= 1986)])
    mk = mk[~np.isnan(mk)]
    out['market'] = dict(sharpe=float(mk.mean() / mk.std() * 12 ** .5))
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'real':
        r = run(); out = evaluate(r)
        json.dump(out, open(OUT + 'ml2_real.json', 'w'), indent=1); print(json.dumps(out, indent=1))
    else:
        k = int(sys.argv[2]); sh = int(np.linspace(60, 180, 20)[k])
        out = evaluate(run(sh)); json.dump(out, open(OUT + 'ml2_null_%02d.json' % k, 'w'), indent=1)
        print(k, sh, out['ic'], out['W1']['sharpe'], flush=True)
