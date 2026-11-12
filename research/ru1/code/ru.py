"""RU1 real-user account engine (2026-11-12). <=2014 data only. See ../PRECOMMIT_RU1.md.
One TQQQ(+USD cash) account that follows a given executed-level series L (level in force on each day, research delay included).
Mirrors acct3 ac3.joint's Z account (MS1 run1 trade logic) exactly when X == 1, no deposits, no harvest, cash 0.
Additions: KRW tax basis with a daily FX index X (KRW per USD / X at start), FX conversion spread at start/end, deposits with the
contract's 4-business-day wait rule. Units: start wealth = 1.0 KRW-unit (= 10M KRW); D = 2.5M/10M = 0.25.
"""
import os, sys, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/ru1_nbcache')
from numba import njit, prange

WARM = 300  # = beng.WARM (checked in the driver)

@njit(cache=True)
def acct(r, rf, L, X, dep, krw_tax, wait, fxc, ccost, ctax, D, er3, cspr, out, Eu, Ek):
    """r, rf, X: length T (path incl. WARM rows; X[WARM] == 1). L, dep: length n = T - WARM.
    krw_tax: 0 = MS1 (USD basis, D in start-USD units), 1 = Korean rule (KRW basis at each trade date's FX, D fixed KRW).
    wait: 1 = contract rule (deposit within 4 business days after an app trade waits for the next level change).
    out: [fin_usd, fin_krw, mdd_usd, mdd_krw, n_trades, tax_paid_krw, deposits_krw, n_waited, cash_days_waited]"""
    n = L.shape[0]
    z0 = 0.0; z3 = 1.0 * (1 - fxc); zb = 0.0; zreal = 0.0; cur = -99.0
    pk_u = 0.0; pk_k = 0.0; mdd_u = 0.0; mdd_k = 0.0
    last_trade = -1000; ntr = 0.0; taxk = 0.0; depk = 0.0; nwait = 0.0; wdays = 0.0; pend = 0.0
    for k in range(n):
        t = k + WARM
        x = X[t]
        if k > 0 and k % 252 == 0:
            due = ctax * max(zreal - D, 0.0); zreal = 0.0           # due in tax currency units
            if due > 0:
                due_u = due / x if krw_tax == 1 else due
                tot = z0 + z3; f = min(due_u / max(tot, 1e-300), 1.0)
                if krw_tax == 1: zreal += f * (z0 * x - zb)
                else: zreal += f * (z0 - zb)
                z0 *= (1 - f); z3 *= (1 - f); zb *= (1 - f)
                taxk += due if krw_tax == 1 else due * x
        if k > 0:
            z0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
            z3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
        # deposit (KRW units) arrives this day
        a = dep[k]
        if a > 0:
            au = a / x * (1 - fxc); depk += a
            tot0 = z0 + z3
            w = z0 / tot0 if tot0 > 0 else 0.0
            z3 += au
            if wait == 1 and k - last_trade <= 4:
                pend += au; nwait += 1
            else:
                buy = w * au
                if buy > 0:
                    tc = ccost * buy; z3 -= buy; z0 += buy - tc
                    zb += buy * x if krw_tax == 1 else buy
        if pend > 0: wdays += 1
        want = L[k]
        if want != cur:
            tot = z0 + z3
            w0 = want / 3; t0 = w0 * tot; t3 = (1 - w0) * tot; d0 = t0 - z0; tc = ccost * abs(d0)
            if d0 < 0 and z0 > 0:
                fr = min(-d0 / z0, 1.0)
                if krw_tax == 1: zreal += fr * (z0 * x - zb)
                else: zreal += fr * (z0 - zb)
                zb *= 1 - fr
            if d0 > 0: zb += d0 * x if krw_tax == 1 else d0
            sc = (tot - tc) / max(tot, 1e-300); z0 = t0 * sc; z3 = t3 * sc; cur = want
            if k > 0: last_trade = k; ntr += 1
            pend = 0.0
        E = z0 + z3
        Eu[k] = E; Ek[k] = E * x
        pk_u = max(pk_u, E); mdd_u = min(mdd_u, E / pk_u - 1)
        pk_k = max(pk_k, E * x); mdd_k = min(mdd_k, E * x / pk_k - 1)
    x = X[WARM + n - 1]
    if krw_tax == 1:
        g = zreal + (z0 * x - zb)
        ft = ctax * max(g - D, 0.0)
        fin_k = (z0 + z3) * x * (1 - fxc) - ft; fin_u = fin_k / x
    else:
        g = zreal + (z0 - zb)
        ft = ctax * max(g - D, 0.0)
        fin_u = z0 + z3 - ft; fin_k = fin_u * x * (1 - fxc)
    taxk += ft * x if krw_tax == 0 else ft
    out[0] = fin_u; out[1] = fin_k; out[2] = mdd_u; out[3] = mdd_k; out[4] = ntr; out[5] = taxk; out[6] = depk; out[7] = nwait
    out[8] = wdays

@njit(parallel=True, cache=True)
def acctP(R, RF, L, XX, DEP, krw_tax, wait, fxc, ccost, ctax, D, er3, cspr):
    P = R.shape[0]; n = L.shape[1]
    out = np.zeros((P, 9)); EU = np.zeros((P, n)); EK = np.zeros((P, n))
    for i in prange(P):
        acct(R[i], RF[i], L[i], XX[i], DEP[i], krw_tax, wait, fxc, ccost, ctax, D, er3, cspr, out[i], EU[i], EK[i])
    return out, EU, EK

def cagr(fin, yrs):
    return np.maximum(fin, 1e-9) ** (1 / yrs) - 1

def stats(fin, E, yrs, ref=None):
    cg = cagr(fin, yrs); m = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
    o = dict(n=int(len(cg)), p50=float(np.median(cg)), mdd_med=float(np.median(m)))
    if len(cg) > 1:
        o.update(p10=float(np.percentile(cg, 10)), p90=float(np.percentile(cg, 90)), dd80=float(np.mean(m <= -0.8)))
    if ref is not None:
        d = cg - ref; o.update(d_med=float(np.median(d)), p_beat=float(np.mean(d > 1e-6)))
    return o, cg

def underwater(E):
    """per path: longest stretch below the running peak (years), share of days below -50%"""
    P, n = E.shape; lo = np.zeros(P); b50 = np.zeros(P)
    for i in range(P):
        e = E[i]; pk = np.maximum.accumulate(e); uw = e < pk * (1 - 1e-9)
        best = run = 0
        for v in uw:
            run = run + 1 if v else 0; best = max(best, run)
        lo[i] = best / 252; b50[i] = np.mean(e <= 0.5 * pk)
    return lo, b50
