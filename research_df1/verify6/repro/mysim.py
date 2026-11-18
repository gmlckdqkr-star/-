"""Independent numpy re-implementation of the DF6 accounting (verifier). Data <= 2014-12-31 only.
Semantics re-derived from reading dfk.run1 (not calling it): WARM=300; yearly tax at k%252==0 on realized-D (proportional sale),
returns applied k>0 (income part taxed 15.4%, net income added to basis), rebalance at k==0 and k%R==0 (forced, no delay since
static weights), year-end harvest k%252==251 (both directions, threshold tax*|rz| > 2*cost*sv), daily MDD on account value,
final liquidation tax on realized+unrealized-D."""
import numpy as np, pandas as pd
WARM = 300
END = pd.Timestamp('2014-12-31')
CLEAN = '/mnt/project-files/research/df5/data/clean/'

def load_csv(name, cut=END):
    s = pd.read_csv(CLEAN + name + '.csv', parse_dates=['date']).set_index('date')['r'].astype(float)
    return s[s.index <= cut]          # cut at load

def def3_series(cut=END):
    a, b, c = load_csv('STAP', cut), load_csv('HLTH', cut), load_csv('UTIL', cut)
    i = a.index.intersection(b.index).intersection(c.index)
    return (a.reindex(i) + b.reindex(i) + c.reindex(i)) / 3.0

def sim(RET, INC, w, reb=0, cost=0.003, tax=0.22, D=0.25, harvest=True, hthr=1.0, reb_days=None, Th=None, snaps=()):
    """RET (P,T,K) daily net returns; INC (P,T,K) or (K,) income rate per day (taxed 15.4%); w (K,) static target weights.
    reb: forced rebalance every reb days (k%reb==0, k>0); reb_days: explicit set of k values instead. Returns (fin, mdd)."""
    RET = np.asarray(RET, float)
    P, T, K = RET.shape
    if Th is not None: T = Th
    w = np.asarray(w, float)
    INC = np.asarray(INC, float)
    inc_const = INC.ndim == 1
    v = np.zeros((P, K)); b = np.zeros((P, K)); vc = np.zeros(P)
    real = np.zeros(P); gpk = np.ones(P); mdd = np.zeros(P); E = np.ones(P)
    rebset = set(reb_days) if reb_days is not None else None
    SN = {}
    for t in range(WARM, T):
        k = t - WARM
        if k > 0 and k % 252 == 0:
            due = tax * np.maximum(real - D, 0.0); real = np.zeros(P)
            tot = vc + v.sum(1)
            f = np.where(due > 0, np.minimum(due / np.maximum(tot, 1e-300), 1.0), 0.0)
            real += (f[:, None] * (v - b)).sum(1)
            v *= (1 - f)[:, None]; b *= (1 - f)[:, None]; vc *= (1 - f)
        if k > 0:
            inc = INC if inc_const else INC[:, t, :]
            b += v * inc * (1 - 0.154)
            v *= (1 + RET[:, t, :] - 0.154 * inc)
        if k == 0:
            tot = np.ones(P); tg = w[None, :] * tot[:, None]
            tc = cost * np.abs(tg).sum(1)
            b = tg.copy(); sc = (tot - tc) / tot
            v = tg * sc[:, None]; vc = (1 - w.sum()) * tot * sc
        else:
            do = (reb_days is None and reb > 0 and k % reb == 0) or (rebset is not None and k in rebset)
            if do:
                tot = vc + v.sum(1); tg = w[None, :] * tot[:, None]; d = tg - v
                tc = cost * np.abs(d).sum(1)
                sell = (d < 0) & (v > 0)
                fr = np.where(sell, np.minimum(-d / np.where(v > 0, v, 1.0), 1.0), 0.0)
                real += (fr * (v - b)).sum(1); b = b * (1 - fr)
                b = b + np.where(d > 0, d, 0.0)
                sc = (tot - tc) / np.maximum(tot, 1e-300)
                v = tg * sc[:, None]; vc = (1 - w.sum()) * tot * sc
        if harvest and k % 252 == 251:
            for i in range(K):
                vi = v[:, i]; ok = vi > 1e-12
                target = D - real; U = vi - b[:, i]
                f = np.zeros(P)
                m1 = ok & (target < 0) & (U < 0); m2 = ok & (target > 0) & (U > 0)
                Us = np.where(U != 0, U, 1.0)
                f = np.where(m1 | m2, np.minimum(1.0, target / Us), 0.0)
                rz = f * U; sv = f * vi
                go = (sv > 0) & (tax * np.abs(rz) > hthr * 2 * cost * sv)
                tc = 2 * cost * sv
                real = np.where(go, real + rz, real)
                b[:, i] = np.where(go, b[:, i] - (sv - rz) + (sv - tc), b[:, i])
                v[:, i] = np.where(go, vi - tc, vi)
        E = vc + v.sum(1)
        gpk = np.maximum(gpk, E); mdd = np.minimum(mdd, E / gpk - 1)
        if t + 1 in snaps:
            SN[t + 1] = (E - tax * np.maximum(real + (v - b).sum(1) - D, 0.0), mdd.copy())
    unr = (v - b).sum(1)
    fin = E - tax * np.maximum(real + unr - D, 0.0)
    if snaps: return fin, mdd, SN
    return fin, mdd

def cagr(fin, T):
    yrs = (T - WARM) / 252
    return np.maximum(fin, 1e-9) ** (1 / yrs) - 1

def summ(cg, md, qcg=None):
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd_med=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
    if qcg is not None: d['pair'] = float(np.median(cg - qcg)); d['win'] = float(np.mean(cg > qcg))
    return d
