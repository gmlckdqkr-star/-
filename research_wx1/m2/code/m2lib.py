"""M2 shared library: data, signal groups, past-only weights (EQ / ICW / RIDGE, regime-conditional), composites, IC,
fast pre-tax book engine (numba). Pre-registration: research/wx1/m2/PRECOMMIT_M2.md (sha e5454014...).
Scores at decision j read OAP row M-2 (built in build_data.py) and holding returns realized before D_j only."""
import os, numpy as np, pandas as pd
from numba import njit

SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m2'
GROUPS = {'VALUE': ['valuation', 'leverage', 'long term reversal'],
          'PROFIT': ['profitability', 'profitability alt', 'composite accounting', 'earnings growth', 'payout indicator',
                     'cash flow risk', 'default risk'],
          'INVEST': ['investment', 'investment alt', 'investment growth', 'asset composition', 'accruals',
                     'external financing', 'sales growth', 'R&D'],
          'MOMENTUM': ['momentum', 'lead lag', 'short-term reversal'],
          'RISK': ['risk', 'volatility', 'liquidity', 'volume', 'optionrisk', 'informed trading'],
          'ANALYST': ['earnings forecast', 'recommendation', 'earnings event', 'info proxy'],
          'OTHER': ['other', 'ownership', 'short sale constraints']}
GNAMES = list(GROUPS)
COST = 0.003
ICWIN, ICMIN, REGMIN, LAM = 120, 36, 24, 1.0


class Data:
    pass


def load(path=os.path.join(SCR, 'm2data.npz'), cov=os.path.join(SCR, 'coverage.csv')):
    z = np.load(path)
    d = Data()
    for k in z.files:
        setattr(d, k, z[k])
    d.dd = pd.to_datetime(d.ddate.astype('datetime64[D]'))
    d.yr = d.dd.year.values
    d.mo = d.dd.month.values
    d.nd, d.N, d.S = d.SR.shape
    cv = pd.read_csv(cov).set_index('sig')
    d.keep = np.array([bool(cv.loc[c, 'keep']) for c in d.cols])
    inv = {e: g for g, es in GROUPS.items() for e in es}
    d.grp_of = np.array([inv[e] for e in d.econ])
    present = np.isfinite(d.SR)
    d.cnt = present.sum(1)                                     # [nd, S] names with a value
    d.U = (d.yr[:, None] >= d.year[None, :] + 1) & (d.cnt >= 30) & d.keep[None, :]   # usable (publication rule)
    d.R0 = np.nan_to_num(d.SR, nan=0.0)                       # float32
    d.Pm = present.astype(np.float32)
    d.SR = None
    return d


def subsets(d):
    """17 pre-registered subsets -> bool mask over signals (keep only)."""
    out = {'ALL': d.keep.copy()}
    for g in GNAMES:
        out[g] = d.keep & (d.grp_of == g)
    for g in GNAMES:
        out['ex' + g] = d.keep & (d.grp_of != g)
    out['CLEAR'] = d.keep & (d.pq == '1_clear')
    med = np.nanmedian(d.tstat[d.keep])
    out['TOPT'] = d.keep & (np.nan_to_num(d.tstat, nan=-1) >= med)
    return out


def def_mask(d):
    return d.keep & np.isin(d.grp_of, ['PROFIT', 'RISK'])


def ranks_ret(d):
    """centered rank of the holding return among eligible names [nd, N] (NaN outside)."""
    X = np.where(d.elig, d.HR, np.nan)
    Rk = pd.DataFrame(X).rank(axis=1, method='average')
    n = Rk.notna().sum(axis=1).values[:, None]
    return ((Rk.values - 0.5) / np.maximum(n, 1) - 0.5)


def signal_ic(d, RR):
    """monthly rank IC per signal: Pearson(centered signal rank, centered return rank) over names with both."""
    ic = np.full((d.nd, d.S), np.nan)
    for j in range(d.nd):
        y = RR[j]; ok = np.isfinite(y)
        X = d.R0[j][ok]; P = d.Pm[j][ok]; yy = y[ok]
        n = P.sum(0)
        sx = (X * P).sum(0); sy = (P * yy[:, None]).sum(0)
        sxx = (X * X * P).sum(0); syy = (P * (yy ** 2)[:, None]).sum(0); sxy = (X * yy[:, None] * P).sum(0)
        with np.errstate(all='ignore'):
            cov = sxy / n - sx * sy / n ** 2
            vx = sxx / n - (sx / n) ** 2; vy = syy / n - (sy / n) ** 2
            c = cov / np.sqrt(vx * vy)
        c[n < 30] = np.nan
        ic[j] = c
    return ic


def signal_corr(d):
    """monthly cross-sectional correlation matrices of signal ranks (missing = 0) [nd, S, S] float32."""
    C = np.zeros((d.nd, d.S, d.S), np.float32)
    for j in range(d.nd):
        X = d.R0[j][d.elig[j]].astype(np.float64)
        cv = X.T @ X / max(len(X), 1)
        s = np.sqrt(np.maximum(np.diag(cv), 1e-12))
        c = cv / s[:, None] / s[None, :]
        c[np.diag(cv) < 1e-10, :] = 0; c[:, np.diag(cv) < 1e-10] = 0
        C[j] = c
    return C


def past_means(ic, C, regime=None, win=ICWIN, minm=ICMIN):
    """For each decision j: mean IC m[j, s] and mean corr Cbar[j] over the past window (j' <= j-2). regime: None =
    last `win` months; else bool [nd] -> all past months with regime[j'] == regime[j] (min REGMIN), returns also ok[j].
    Months with NaN IC count as missing for that signal."""
    nd, S = ic.shape
    v = np.isfinite(ic); x = np.where(v, ic, 0.0)
    m = np.zeros((nd, S)); ok = np.zeros(nd, bool); Cb = np.zeros((nd, S, S), np.float32)
    if regime is None:
        cx = np.vstack([np.zeros((1, S)), np.cumsum(x, 0)]); cv_ = np.vstack([np.zeros((1, S)), np.cumsum(v, 0)])
        cC = np.concatenate([np.zeros((1, S, S)), np.cumsum(C, 0, dtype=np.float64)], 0)
        for j in range(nd):
            hi = j - 1                     # use rows < hi  (j' <= j-2)
            lo = max(0, hi - win)
            if hi - lo < minm:
                continue
            n = cv_[hi] - cv_[lo]
            with np.errstate(all='ignore'):
                m[j] = np.where(n >= minm // 2, (cx[hi] - cx[lo]) / n, 0.0)
            Cb[j] = (cC[hi] - cC[lo]) / (hi - lo)
            ok[j] = True
        return m, Cb, ok
    for r in (False, True):
        sel = (regime == r)
        xr = np.where(sel[:, None], x, 0.0); vr = np.where(sel[:, None], v, False)
        cx = np.vstack([np.zeros((1, S)), np.cumsum(xr, 0)]); cv_ = np.vstack([np.zeros((1, S)), np.cumsum(vr, 0)])
        cnt = np.r_[0, np.cumsum(sel)]
        cC = np.concatenate([np.zeros((1, S, S)), np.cumsum(np.where(sel[:, None, None], C, 0), 0, dtype=np.float64)], 0)
        for j in np.flatnonzero(sel):
            hi = j - 1
            if hi <= 0:
                continue
            k = cnt[hi]
            if k < REGMIN:
                continue
            n = cv_[hi]
            with np.errstate(all='ignore'):
                m[j] = np.where(n >= REGMIN // 2, cx[hi] / n, 0.0)
            Cb[j] = cC[hi] / k
            ok[j] = True
    return m, Cb, ok


def weights(d, mask, wkind, est, est_unc=None, rows=None):
    """[nd, S] weights for subset mask. wkind EQ / ICW / RIDGE. est = (m, Cb, ok) from past_means (None for plain EQ).
    est_unc: fallback estimate (unconditional) where est is not ok (regime-conditional C4/C5)."""
    U = d.U & mask[None, :]
    if est is None:
        return U.astype(np.float64)
    m, Cb, ok = est
    W = np.zeros((d.nd, d.S))
    for j in (range(d.nd) if rows is None else rows):
        u = np.flatnonzero(U[j])
        if len(u) == 0:
            continue
        mj, Cj, okj = m[j], Cb[j], ok[j]
        if not okj and est_unc is not None:
            mj, Cj, okj = est_unc[0][j], est_unc[1][j], est_unc[2][j]
        if not okj:
            W[j, u] = 1.0
            continue
        if wkind == 'EQ':            # regime-conditional EQ: signals with positive past same-regime mean IC
            w = (mj[u] > 0).astype(float)
        elif wkind == 'ICW':
            w = np.maximum(mj[u], 0.0)
        else:
            A = Cj[np.ix_(u, u)].astype(np.float64) + LAM * np.eye(len(u))
            w = np.linalg.solve(A, mj[u])
        if not np.abs(w).sum() > 0:
            w = np.ones(len(u))
        W[j, u] = w
    return W


def composite(d, W, rows=None):
    """score [nd, N] = sum w r / sum |w| present, NaN if presence weight < 1/3 of the usable weight or not eligible.
    rows: slice of decisions to compute (others NaN)."""
    rs = slice(0, d.nd) if rows is None else rows
    W32 = W[rs].astype(np.float32); A32 = np.abs(W32)
    num = np.matmul(d.R0[rs], W32[:, :, None])[:, :, 0]
    den = np.matmul(d.Pm[rs], A32[:, :, None])[:, :, 0]
    tot = A32.sum(1)[:, None]
    with np.errstate(all='ignore'):
        part = num / den
    part[(den < tot / 3.0) | (tot <= 0) | ~d.elig[rs]] = np.nan
    sc = np.full((d.nd, d.N), np.nan)
    sc[rs] = part
    return sc


def sector_neutral(d, sc, rows=None):
    """within pseudo-sector percentile (average-free: ordinal within group, (pos+0.5)/n)."""
    out = np.full_like(sc, np.nan)
    for j in (range(d.nd) if rows is None else range(rows.start, rows.stop)):
        s = sc[j]; f = np.flatnonzero(np.isfinite(s))
        if len(f) == 0:
            continue
        g = d.grp[j][f].astype(np.int64)
        o = np.lexsort((s[f], g))
        gs = g[o]
        start = np.r_[0, np.flatnonzero(gs[1:] != gs[:-1]) + 1]
        cnt = np.diff(np.r_[start, len(gs)])
        first = np.repeat(start, cnt); n = np.repeat(cnt, cnt)
        pos = np.arange(len(gs)) - first
        out[j, f[o]] = (pos + 0.5) / n
    return out


def ic_series(d, sc, RR):
    out = np.full(d.nd, np.nan)
    for j in range(d.nd):
        m = np.isfinite(sc[j]) & np.isfinite(RR[j])
        if m.sum() > 30:
            a = pd.Series(sc[j][m]).rank().values; b = RR[j][m]
            out[j] = np.corrcoef(a, b)[0, 1]
    return out


def top_picks(sc, Kmax=50, seed=7, rows=None):
    """[nd, Kmax] column indices by descending score (-1 = none). Ties broken by a fixed random draw (not column order)."""
    nd, N = sc.shape
    out = np.full((nd, Kmax), -1, np.int64)
    tb = np.random.default_rng(seed).random(N) * 1e-12
    for j in (range(nd) if rows is None else range(rows.start, rows.stop)):
        s = sc[j]
        f = np.flatnonzero(np.isfinite(s))
        if len(f) == 0:
            continue
        o = f[np.argsort(-(s[f] + tb[f]), kind='stable')][:Kmax]
        out[j, :len(o)] = o
    return out


@njit(cache=True)
def _book(picks, K, HR, CR, gate, sched, j0, j1, cost):
    """One sub-book: decisions at rows where sched[j] is True (j0 <= j < j1), hold until the next one. Before its first
    decision the capital sits in cash. Returns value path V[j0..j1] (len j1-j0+1), start value 1."""
    nm = j1 - j0
    V = np.ones(nm + 1)
    N = HR.shape[1]
    hidx = np.full(K, -1, np.int64)
    hval = np.zeros(K)
    cash = 1.0
    tmp = np.zeros(N)
    for t in range(nm):
        j = j0 + t
        if sched[j]:
            tot = cash
            for i in range(K):
                if hidx[i] >= 0:
                    tot += hval[i]
                    tmp[hidx[i]] += hval[i]
            n = 0
            if gate[j]:
                for i in range(K):
                    if picks[j, i] >= 0:
                        n += 1
            tgt = tot / K
            tr = 0.0
            for i in range(K):
                p = picks[j, i] if gate[j] else -1
                if p >= 0:
                    tr += abs(tgt - tmp[p])
                    tmp[p] = -1e300          # mark as new target name
            for i in range(K):
                if hidx[i] >= 0 and tmp[hidx[i]] > -1e299:
                    tr += tmp[hidx[i]]       # sold out
            for i in range(K):               # reset tmp
                if hidx[i] >= 0:
                    tmp[hidx[i]] = 0.0
            for i in range(K):
                p = picks[j, i]
                if p >= 0:
                    tmp[p] = 0.0
            c = cost * tr
            tot2 = tot - c
            cash = tot2
            for i in range(K):
                p = picks[j, i] if gate[j] else -1
                if p >= 0:
                    hidx[i] = p
                    hval[i] = tot2 / K
                    cash -= tot2 / K
                else:
                    hidx[i] = -1
                    hval[i] = 0.0
        v = cash * (1.0 + CR[j])
        cash = cash * (1.0 + CR[j])
        for i in range(K):
            if hidx[i] >= 0:
                hval[i] *= (1.0 + HR[j, hidx[i]])
                v += hval[i]
        V[t + 1] = v
    return V


def book_returns(picks, K, HR, CR, gate, mo, j0, j1, rb, cost=COST):
    """monthly returns [j1-j0] of a top-K book. rb: 'M' monthly, 'Q' quarterly (Jan/Apr/Jul/Oct), 'T' 3 tranches."""
    nd = len(CR)
    P = np.ascontiguousarray(picks[:, :K])
    if rb == 'M':
        sched = np.ones(nd, np.bool_)
        V = _book(P, K, HR, CR, gate, sched, j0, j1, cost)
    elif rb == 'Q':
        sched = np.isin(mo, [1, 4, 7, 10])
        V = _book(P, K, HR, CR, gate, sched, j0, j1, cost)
    else:
        V = np.zeros(j1 - j0 + 1)
        for k in range(3):
            sched = (np.arange(nd) - j0) % 3 == k
            V += _book(P, K, HR, CR, gate, sched, j0, j1, cost) / 3.0
    return V[1:] / V[:-1] - 1.0


def ew_returns(d, j0, j1, cost=COST):
    """equal-weight eligible members, monthly rebalance with drift turnover cost (initial buy included)."""
    r = np.zeros(j1 - j0)
    wprev = None
    for t, j in enumerate(range(j0, j1)):
        e = d.elig[j]; n = e.sum()
        w = np.where(e, 1.0 / n, 0.0)
        tr = np.abs(w).sum() if wprev is None else np.abs(w - wprev).sum()
        g = np.where(e, d.HR[j], 0.0)
        rp = (w * g).sum()
        r[t] = (1 - cost * tr) * (1 + rp) - 1
        wprev = w * (1 + g) / (1 + rp)
    return r
