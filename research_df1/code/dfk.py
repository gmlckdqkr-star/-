"""DF5 K-asset engine: same day order and the same cost / tax / deduction / harvest / final liquidation tax / delay queue as dfe.py,
but with K arbitrary assets and exogenous target weights.
  RET (P,T,K)  daily asset return (already net of the asset's expense ratio; leveraged ETFs built outside, e.g. 3r-2rf-er3/252)
  INC (P,T,K)  daily income part of RET taxed at 15.4% when paid (bond coupon, T-bill yield, dividend estimate); added to cost basis
  W   (P,T,K)  target weights decided at close t (sum <= 1; the rest is cash at 0 interest)
  EV  (P,T)    True where the decision at close t is a new target (trade); executed at close t+delay like dfe
  HV  (K,)     1 = normal asset, harvestable at year end (dfe: TQQQ, QQQ, bond); 2 = T-bill-like (whole return is income taxed 15.4%,
               basis follows it, never harvested; INC ignored); 0 = normal but not harvestable
All decisions use information at close t only. <=2014 data only (inputs are built from <=2014 calendars)."""
import numpy as np
from numba import njit, prange
WARM = 300

@njit(cache=True)
def run1(RET, INC, W, EV, HV, delay, cost, tax, D, harvest, hthr, reb_every, out, rec, recon):
    T, K = RET.shape
    v = np.zeros(K); b = np.zeros(K); vc = 0.0
    real = 0.0; due = 0.0
    gpk = 1.0; mdd = 0.0; E = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0
    lastdec = -1
    for t in range(WARM, T):
        k = t - WARM
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = vc
                for i in range(K): tot += v[i]
                taxp += due
                f = min(due / max(tot, 1e-300), 1.0)
                for i in range(K):
                    real += f * (v[i] - b[i]); v[i] *= (1 - f); b[i] *= (1 - f)
                vc *= (1 - f)
                due = 0.0
        dec = t - delay
        if dec < WARM - 1: dec = WARM - 1
        if k > 0:
            for i in range(K):
                if HV[i] == 2:                 # T-bill-like: the whole return is taxed income (dfe asset 3 rule)
                    y = RET[t, i]
                    if y > 0: y *= (1 - 0.154)
                    b[i] += v[i] * y; v[i] *= (1 + y)
                else:
                    inc = INC[t, i]
                    b[i] += v[i] * inc * (1 - 0.154)
                    v[i] *= (1 + RET[t, i] - 0.154 * inc)
        forced = reb_every > 0 and k > 0 and k % reb_every == 0
        trade = (k == 0) or (dec != lastdec and EV[dec]) or forced
        if dec != lastdec and EV[dec]: lastdec = dec
        if k == 0: lastdec = dec
        if trade:
            # target = most recent decided weights up to dec
            j = dec
            while j > WARM - 1 and not EV[j]: j -= 1
            tot = vc
            for i in range(K): tot += v[i]
            if k == 0:
                tot = 1.0; vc = 1.0
            tc = 0.0
            tg = np.zeros(K)
            wsum = 0.0
            for i in range(K):
                tg[i] = W[j, i] * tot; wsum += W[j, i]
                d = tg[i] - v[i]
                tc += cost * abs(d)
                if d < 0 and v[i] > 0:
                    fr = min(-d / v[i], 1.0); real += fr * (v[i] - b[i]); b[i] *= 1 - fr
                if d > 0: b[i] += d
            costp += tc
            sc = (tot - tc) / max(tot, 1e-300)
            vcash = (1.0 - wsum) * tot
            for i in range(K): v[i] = tg[i] * sc
            vc = vcash * sc
            ntr += 1
        if harvest > 0 and k % 252 == 251:
            for i in range(K):
                if HV[i] == 1 and v[i] > 1e-12:
                    target = D - real
                    U = v[i] - b[i]
                    f = 0.0
                    if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                    if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                    rz = f * U; sv = f * v[i]
                    if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                        tc = 2 * cost * sv; costp += tc
                        real += rz; b[i] = b[i] - (sv - rz) + (sv - tc)
                        v[i] -= tc
        E = vc
        for i in range(K): E += v[i]
        gpk = max(gpk, E); mdd = min(mdd, E / gpk - 1)
        if recon == 1: rec[k] = E
    unr = 0.0
    for i in range(K): unr += v[i] - b[i]
    fin = E - due - tax * max(real + unr - D, 0.0)
    out[0] = fin; out[1] = mdd; out[2] = ntr; out[3] = taxp; out[4] = costp; out[5] = E

@njit(parallel=True, cache=True)
def runP(RET, INC, W, EV, HV, delay, cost, tax, D, harvest, hthr, reb_every, recon):
    P, T, K = RET.shape; out = np.zeros((P, 6)); EE = np.zeros((P, T - WARM)) if recon == 1 else np.zeros((P, 1))
    for p in prange(P):
        rec = np.zeros(T - WARM) if recon == 1 else np.zeros(1)
        run1(RET[p], INC[p], W[p], EV[p], HV, delay, cost, tax, D, harvest, hthr, reb_every, out[p], rec, recon)
        if recon == 1: EE[p] = rec
    return out, EE

DEF = dict(delay=2, cost=0.003, tax=0.22, D=0.25, harvest=3, hthr=1.0, reb_every=0)

def run(RET, INC, W, EV, HV, recon=False, **kw):
    p = dict(DEF); p.update(kw)
    f = lambda a, dt=np.float64: np.ascontiguousarray(a, dtype=dt)
    return runP(f(RET), f(INC), f(W), f(EV, np.bool_), f(HV, np.int64), int(p['delay']), p['cost'], p['tax'], p['D'], int(p['harvest']),
                p['hthr'], int(p['reb_every']), 1 if recon else 0)

def stats(out, T):
    yrs = (T - WARM) / 252
    cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    return cg, out[:, 1]
