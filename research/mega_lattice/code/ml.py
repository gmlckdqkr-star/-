"""Mega-lattice pipeline (PRECOMMIT_ML.md). Data <= 2014-12-31 only.
build() -> data dict (cached to results/cache_build.npz is NOT done: rebuild is ~1 min)."""
import sys, itertools, numpy as np, pandas as pd, numba as nb, zipfile, io
sys.path.insert(0, '/mnt/project-files/research/c3_create/code')
sys.path.insert(0, '/mnt/project-files/research/mega_lattice/code')
import feat
END = pd.Timestamp('2014-12-31')
Y0 = 1926; NY = 2015 - Y0
KAPPA = 2000.0
H0, H1 = 3, 23            # label window t+3..t+23 (G1 window)


def rf_daily():
    t = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/TBILL_daily_1927_2014.csv', parse_dates=['date'])
    return (t.set_index('date')['rate_known_pct'] / 100 / 252)


def kf6():
    z = zipfile.ZipFile('/mnt/project-files/research/data/ken_french/raw/cur/6_Portfolios_2x3_daily_CSV.zip')
    lines = z.read(z.namelist()[0]).decode('latin1').splitlines()
    i0 = [i for i, l in enumerate(lines) if 'Average Value Weighted Returns -- Daily' in l][0]
    rows = []
    for l in lines[i0 + 2:]:
        parts = [x.strip() for x in l.split(',')]
        if len(parts) < 7 or not parts[0].isdigit():
            break
        rows.append([parts[0]] + [float(x) for x in parts[1:7]])
    df = pd.DataFrame(rows, columns=['d', 'SL', 'S2', 'SH', 'BL', 'B2', 'BH'])
    df.index = pd.to_datetime(df['d'], format='%Y%m%d'); df = df.drop(columns='d')
    df = df[df.index <= END]
    out = {}
    for c in df.columns:
        r = df[c].where(df[c] > -99) / 100
        out['KF_' + c] = (1 + r.fillna(0)).cumprod()
    return out


def markets():
    import ev
    S = ev.series()
    S.update(kf6())
    return {k: v[v.index <= END].dropna() for k, v in S.items()}


def market_rows(name, p, rf):
    p = p[~p.index.duplicated(keep='last')]
    D = feat.feats(p, p.index.month)
    lp = np.log(p.values); n = len(p)
    rfa = rf.reindex(p.index, method='ffill').fillna(0.0).values
    crf = np.r_[0, np.cumsum(rfa)]
    y = np.full(n, np.nan); last = np.full(n, -1)
    for t in range(n - H1):
        y[t] = lp[t + H1] - lp[t + H0 - 1] - (crf[t + H1 + 1] - crf[t + H0])
        last[t] = t + H1
    yrs = p.index.year.values
    avail = np.where(last >= 0, yrs[np.clip(last, 0, n - 1)], 9999)
    return dict(name=name, dates=p.index, D=D, y=y, up=(y > 0).astype(float), avail=avail, year=yrs,
                fold=(yrs // 5) % 2, tidx=np.arange(n), price=p)


def sublattices(K=40, ntri=3000, seed=20261104):
    subs = [(i, -1, -1) for i in range(K)] + [(i, j, -1) for i, j in itertools.combinations(range(K), 2)]
    allt = list(itertools.combinations(range(K), 3))
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(allt), ntri, replace=False)
    subs += [allt[k] for k in sorted(pick)]
    subs = np.array(subs, np.int64)
    size = np.where(subs[:, 2] >= 0, 125, np.where(subs[:, 1] >= 0, 25, 5))
    off = np.r_[0, np.cumsum(size)[:-1]].astype(np.int64)
    return subs, off, int(size.sum())


def make_edges(rows_list):
    """quantile edges from pooled training rows whose label ends before 1986 (fixed)."""
    E = {}
    for nm in feat.NAMES:
        if nm == 'season':
            E[nm] = None; continue
        v = np.concatenate([r['D'][nm].values[r['avail'] < 1986] for r in rows_list])
        v = v[~np.isnan(v)]
        q = np.unique(np.quantile(v, [.2, .4, .6, .8]))
        E[nm] = q
    return E


@nb.njit(cache=True)
def _accum(B, valid, y, up, fold, yr, subs, off, SY, NN, SU):
    n = B.shape[0]; S = subs.shape[0]
    for i in range(n):
        if not valid[i]:
            continue
        g = fold[i]; k = yr[i]
        for s in range(S):
            c = off[s] + B[i, subs[s, 0]]
            if subs[s, 1] >= 0:
                c += 5 * B[i, subs[s, 1]]
            if subs[s, 2] >= 0:
                c += 25 * B[i, subs[s, 2]]
            SY[g, k, c] += y[i]; NN[g, k, c] += 1.0; SU[g, k, c] += up[i]


@nb.njit(cache=True)
def _score(B, subs, off, dA, dB):
    n = B.shape[0]; S = subs.shape[0]
    oa = np.zeros(n); ob = np.zeros(n)
    for i in range(n):
        a = 0.0; b = 0.0
        for s in range(S):
            c = off[s] + B[i, subs[s, 0]]
            if subs[s, 1] >= 0:
                c += 5 * B[i, subs[s, 1]]
            if subs[s, 2] >= 0:
                c += 25 * B[i, subs[s, 2]]
            a += dA[c]; b += dB[c]
        oa[i] = a / S; ob[i] = b / S
    return oa, ob


class Lattice:
    def __init__(self, rows_list, edges, subs, off, ncell, shift=0, kappa=KAPPA):
        self.subs, self.off, self.ncell, self.kappa = subs, off, ncell, kappa
        self.R = []
        for r in rows_list:
            B = feat.binize(r['D'], edges)
            if shift:
                B = np.roll(B, shift % len(B), axis=0)
            valid = (B.min(1) >= 0) & ~np.isnan(r['y'])
            self.R.append(dict(r, B=B, valid=valid, fvalid=(B.min(1) >= 0)))
        SY = np.zeros((2, NY, ncell)); NN = np.zeros((2, NY, ncell)); SU = np.zeros((2, NY, ncell))
        for r in self.R:
            yr = np.clip(r['avail'] - Y0, 0, NY - 1).astype(np.int64)
            ok = r['valid'] & (r['avail'] <= 2014)
            _accum(r['B'], ok, np.nan_to_num(r['y']), r['up'], r['fold'].astype(np.int64), yr, subs, off, SY, NN, SU)
        self.SY = np.cumsum(SY, axis=1); self.NN = np.cumsum(NN, axis=1); self.SU = np.cumsum(SU, axis=1)
        self._cal = {}

    def deltas(self, Y):
        """tables from rows with avail year < Y  -> (dA, dB, ybar_g, ubar_g, dU_A, dU_B)"""
        k = Y - 1 - Y0
        out = []
        for g in (0, 1):
            sy, nn, su = self.SY[g, k], self.NN[g, k], self.SU[g, k]
            tot_n = nn[:5].sum(); yb = sy[:5].sum() / tot_n
            out.append((sy - nn * yb) / (nn + self.kappa))
        return out[0], out[1]

    def calib(self, Y):
        if Y in self._cal:
            return self._cal[Y]
        dA, dB = self.deltas(Y)
        xs, ys, us = [], [], []
        for r in self.R:
            m = r['valid'] & (r['avail'] < Y) & (r['tidx'] % 21 == 0)
            if not m.any():
                continue
            oa, ob = _score(r['B'][m], self.subs, self.off, dA, dB)
            g = r['fold'][m]
            xs.append(np.where(g == 0, ob, oa)); ys.append(r['y'][m]); us.append(r['up'][m])
        x = np.concatenate(xs); y = np.concatenate(ys); u = np.concatenate(us)
        b, a = np.polyfit(x, y, 1)
        c = logit_fit(x, u)
        res = dict(a=a, b=b, c0=c[0], c1=c[1], ybar=float(y.mean()), pbar=float(u.mean()),
                   mu_med=float(np.median(a + b * x)), n=len(x))
        self._cal[Y] = res
        return res

    def predict(self, r, mode, ymin=1955):
        """mode 'F' (tables as of 1986) or 'E' (refit each Jan 1). returns DataFrame mu, P, S for rows with features."""
        idx = np.where(r['fvalid'] & (r['year'] >= ymin))[0]
        S = np.full(len(r['y']), np.nan); MU = S.copy(); P = S.copy(); MED = S.copy()
        years = r['year'][idx] if mode == 'E' else np.full(len(idx), 1986)
        for Y in np.unique(years):
            ii = idx[years == Y]
            dA, dB = self.deltas(int(Y))
            oa, ob = _score(r['B'][ii], self.subs, self.off, dA, dB)
            s = (oa + ob) / 2; c = self.calib(int(Y))
            S[ii] = s; MU[ii] = c['a'] + c['b'] * s; P[ii] = 1 / (1 + np.exp(-(c['c0'] + c['c1'] * s))); MED[ii] = c['mu_med']
        return pd.DataFrame(dict(S=S, mu=MU, P=P, mu_med=MED, y=r['y']), index=r['dates'])


def logit_fit(x, u, it=25):
    X = np.c_[np.ones_like(x), x]; w = np.zeros(2)
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-9 * np.eye(2); g = X.T @ (u - p)
        w = w + np.linalg.solve(H, g)
    return w


def build():
    rf = rf_daily(); M = markets()
    rows = [market_rows(k, v, rf) for k, v in M.items()]
    edges = make_edges(rows)
    subs, off, ncell = sublattices()
    return rows, edges, subs, off, ncell
