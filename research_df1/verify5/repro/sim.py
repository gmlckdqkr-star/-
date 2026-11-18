"""Independent after-tax K-asset portfolio simulator (numpy, vectorised over paths, loop over days).
Conventions re-implemented from reading dfe.run1 / PRECOMMIT_DF5 sec 0 (NOT calling dfe/dfk/df5fam):
 - start: at close of day WARM buy targets with 0.3% cost on traded notional; cost lowers value, basis = notional bought
 - daily: asset value *= 1 + RET - 0.154*INC (income taxed 15.4% when paid, after-tax income added to basis);
          HV==2 (T-bill ETF): whole return is income, positive part taxed 15.4%, basis follows value
 - trades: decided at close t, executed at close t+delay to the decided weights; cost 0.3% * |traded| ; sells realise
           pro-rata gains; forced rebalance every reb_every days (k%reb==0)
 - yearly (k%252==0, k>0): tax 22% on (realised gains of the past 252 days - 0.25 deduction), paid by pro-rata sale
 - year end (k%252==251): harvest gains up to the deduction / losses against realised gains (sell+rebuy, 2x cost),
   only if tax effect > round-trip cost
 - end: final value minus 22% * max(realised + unrealised - 0.25, 0); MDD on daily pre-liquidation account value."""
import numpy as np
WARM = 300; TAX = 0.22; DED = 0.25; ITAX = 0.154

def sim(RET, INC, HV, W, EV=None, reb_every=0, Th=None, cost=0.003, delay=2, tax=TAX, D=DED, twr=False):
    P, T0, K = RET.shape
    T = Th if Th else T0
    HV = np.asarray(HV)
    if EV is None:
        EV = np.zeros((P, T0), bool); EV[:, WARM - 1] = True
    # last decision index <= t (per path)
    idx = np.where(EV, np.arange(T0)[None, :], -1); lastev = np.maximum.accumulate(idx, axis=1)
    v = np.zeros((P, K)); b = np.zeros((P, K)); vc = np.zeros(P); real = np.zeros(P)
    gpk = np.ones(P); mdd = np.zeros(P); E = np.ones(P); due = np.zeros(P)
    hv2 = HV == 2; hv1 = np.where(HV == 1)[0]
    pr = np.arange(P)
    Iw = np.ones(P); Ipk = np.ones(P); Imdd = np.zeros(P); Eprev = np.ones(P)
    for t in range(WARM, T):
        k = t - WARM
        wd = np.zeros(P)
        if k > 0 and k % 252 == 0:
            due = tax * np.maximum(real - D, 0.0); real = np.zeros(P)
            tot = vc + v.sum(1); f = np.minimum(due / np.maximum(tot, 1e-300), 1.0); wd = f * tot
            real += f * (v - b).sum(1); v *= (1 - f)[:, None]; b *= (1 - f)[:, None]; vc *= (1 - f); due = np.zeros(P)
        if k > 0:
            R = RET[:, t, :]; I = INC[:, t, :]
            y2 = np.where(R > 0, R * (1 - ITAX), R)
            b += np.where(hv2[None, :], v * y2, v * I * (1 - ITAX))
            v *= np.where(hv2[None, :], 1 + y2, 1 + R - ITAX * I)
        dec = max(t - delay, WARM - 1)
        if k == 0:
            mask = np.ones(P, bool)
        else:
            mask = EV[:, dec].copy() if dec != max(t - 1 - delay, WARM - 1) else np.zeros(P, bool)
            if reb_every > 0 and k % reb_every == 0: mask[:] = True
        if mask.any():
            j = lastev[:, dec]
            Wt = W[pr, j, :]                                  # (P,K)
            tot = vc + v.sum(1)
            if k == 0:
                tot = np.ones(P); vc = np.ones(P)
            tg = Wt * tot[:, None]; d = tg - v
            tc = cost * np.abs(d).sum(1)
            sell = (d < 0) & (v > 0)
            fr = np.where(sell, np.minimum(-d / np.where(v > 0, v, 1.0), 1.0), 0.0)
            rz = (fr * (v - b)).sum(1)
            nb = np.where(sell, b * (1 - fr), b); nb = np.where(d > 0, nb + d, nb)
            sc = (tot - tc) / np.maximum(tot, 1e-300)
            nv = tg * sc[:, None]; nvc = (1.0 - Wt.sum(1)) * tot * sc
            m = mask
            real = np.where(m, real + rz, real)
            b = np.where(m[:, None], nb, b); v = np.where(m[:, None], nv, v); vc = np.where(m, nvc, vc)
        if k % 252 == 251:
            for i in hv1:
                vi = v[:, i]; bi = b[:, i]
                target = D - real; U = vi - bi
                f = np.zeros(P)
                c1 = (target < 0) & (U < 0) & (vi > 1e-12); f = np.where(c1, np.minimum(1.0, target / np.where(U != 0, U, 1)), f)
                c2 = (target > 0) & (U > 0) & (vi > 1e-12); f = np.where(c2, np.minimum(1.0, target / np.where(U != 0, U, 1)), f)
                rz = f * U; sv = f * vi
                ok = (sv > 0) & (tax * np.abs(rz) > 2 * cost * sv)
                tc = 2 * cost * sv
                real = np.where(ok, real + rz, real)
                b[:, i] = np.where(ok, bi - (sv - rz) + (sv - tc), bi)
                v[:, i] = np.where(ok, vi - tc, vi)
        E = vc + v.sum(1)
        gpk = np.maximum(gpk, E); mdd = np.minimum(mdd, E / gpk - 1)
        if twr:
            Iw = Iw * E / np.maximum(Eprev - wd, 1e-300); Ipk = np.maximum(Ipk, Iw); Imdd = np.minimum(Imdd, Iw / Ipk - 1); Eprev = E.copy()
    unr = (v - b).sum(1)
    fin = E - due - tax * np.maximum(real + unr - D, 0.0)
    yrs = (T - WARM) / 252
    cg = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
    if twr: return cg, mdd, fin, Imdd
    return cg, mdd, fin

def summ(cg, md, qcg=None):
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd_med=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
    if qcg is not None: d['pair'] = float(np.median(cg - qcg)); d['win'] = float(np.mean(cg > qcg))
    return d

def sma(lv, n):
    c = np.cumsum(np.c_[np.zeros(lv.shape[0]), lv], axis=1); out = np.full(lv.shape, np.nan)
    out[:, n - 1:] = (c[:, n:] - c[:, :-n]) / n
    return out

def t200(lv):
    s = sma(lv, 200); return np.where(np.isnan(s), False, lv > s)
