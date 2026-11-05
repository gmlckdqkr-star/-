"""MF1 engine: beng.run1 (MS1 F1 chassis) with an MNQ-futures implementation of the same decided level.
mode 0 = original TQQQ+cash (must equal beng.run1 exactly, see p0_parity). mode 1 = futures (see PRECOMMIT_MF1.md).
Futures account: equity A (USD units, start 1), position notional X (fixed contracts, drifts with index),
daily P&L X*(r-rf-s/252), cash interest on A (cmode 0: none, 1: max(rf-2%,0)) taxed 15.4%, 11% yearly tax on net P&L
minus D, contract notional N0 (equity units at start, 0 = continuous) drifting with the index, round-nearest contracts,
fee per side on |dX|, roll every 63 days (2 sides), forced liquidation if A < m*X (extra 1% of X), negative-balance flag."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_brake/code')
import beng
from numba import njit, prange
WARM = beng.WARM
NO = 20

@njit(cache=True)
def run1F(r, rf, B, feat, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
          mode, L3x, N0, cmode, s, fee, m, taxf, daily, out, rec, recon):
    T = r.shape[0]
    v0 = 0.0; v3 = 0.0; b0 = 0.0
    A = 1.0; X = 0.0; Nn = N0
    real = 0.0; due = 0.0
    held = 0.0; cur = -99.0
    q = np.zeros(delay + 1)
    st = np.zeros(32)
    kpk = 1.0; gpk = 1.0; emin = 1.0; mdd = 0.0; E = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0
    E7 = np.nan; E12 = np.nan
    levsum = 0.0; nk = 0.0; nliq = 0.0; neg = 0.0; maxlev = 0.0; dead = False
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if mode == 0:
                if k > 0 and k % 252 == 0:
                    due = tax * max(real - D, 0.0); real = 0.0
                    if due > 0:
                        tot = v0 + v3; taxp += due
                        f = min(due / max(tot, 1e-300), 1.0)
                        real += f * (v0 - b0)
                        v0 *= (1 - f); v3 *= (1 - f); b0 *= (1 - f)
                        due = 0.0
            else:
                if k > 0 and k % 252 == 0:
                    due = taxf * max(real - D, 0.0); real = 0.0
                    if due > 0:
                        A -= due; taxp += due; due = 0.0
            want = q[0]
            for j in range(delay - 1): q[j] = q[j + 1]
            if mode == 0:
                if k > 0:
                    v0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
                    v3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
                if want != cur:
                    tot = v0 + v3
                    if k == 0:
                        tot = 1.0; v3 = 1.0
                    w0 = want / 3
                    t0 = w0 * tot; t3 = (1 - w0) * tot
                    d0 = t0 - v0
                    tc = cost * abs(d0)
                    costp += tc
                    if d0 < 0 and v0 > 0:
                        fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                    if d0 > 0: b0 += d0
                    sc = (tot - tc) / max(tot, 1e-300)
                    v0 = t0 * sc; v3 = t3 * sc
                    cur = want; ntr += 1
                if harvest > 0 and k % 252 == 251 and v0 > 1e-12:
                    target = D - real
                    U = v0 - b0
                    f = 0.0
                    if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                    if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                    rz = f * U; sv = f * v0
                    if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                        tc = 2 * cost * sv; costp += tc
                        real += rz; b0 = b0 - (sv - rz) + (sv - tc)
                        v0 -= tc
                E = v0 + v3
            else:
                if k > 0 and not dead:
                    pl = X * (r[t] - rf[t] - s / 252)
                    A += pl; real += pl
                    if cmode == 1:
                        A += A * max(rf[t] - 0.02 / 252, 0.0) * (1 - 0.154)
                    elif cmode == 2:
                        A += A * 0.007 / 252 * (1 - 0.154)
                    X *= (1 + r[t]); Nn *= (1 + r[t])
                    if X > 0 and k % 63 == 0:
                        tc = 2 * fee * X; A -= tc; real -= tc; costp += tc
                    if A <= 0:
                        neg = 1.0; dead = True; A = 1e-9; X = 0.0
                    elif X > 0 and A < m * X:
                        tc = 0.01 * X; A -= tc; real -= tc; X = 0.0; nliq += 1; cur = -99.0
                        if A <= 0:
                            neg = 1.0; dead = True; A = 1e-9
                if want != cur and not dead:
                    Lx = L3x if want >= 3.0 - 1e-9 else want
                    if N0 > 0:
                        Xn = np.round(Lx * A / Nn) * Nn
                    else:
                        Xn = Lx * A
                    tc = fee * abs(Xn - X)
                    A -= tc; real -= tc; costp += tc
                    if Xn != X: ntr += 1
                    X = Xn; cur = want
                    if A > 0 and X / A > maxlev: maxlev = X / A
                elif daily == 1 and not dead and cur > 0:
                    Lx = L3x if cur >= 3.0 - 1e-9 else cur
                    if N0 > 0:
                        Xn = np.round(Lx * A / Nn) * Nn; go = abs(Xn - X) > 0.5 * Nn
                    else:
                        Xn = Lx * A; go = abs(Xn - X) > 0.05 * Xn
                    if go:
                        tc = fee * abs(Xn - X); A -= tc; real -= tc; costp += tc; X = Xn; ntr += 1
                        if A > 0 and X / A > maxlev: maxlev = X / A
                E = A
            gpk = max(gpk, E); emin = min(emin, E); mdd = min(mdd, E / gpk - 1)
            if k == 7 * 252 - 1: E7 = E
            if k == 12 * 252 - 1: E12 = E
            if mode == 0:
                levsum += cur if cur > 0 else 0.0
            else:
                levsum += X / max(A, 1e-12)
            nk += 1
            kpk = max(kpk, E)
        b = B[t]
        if np.isnan(b): b = 0.0
        tg = bfn(t - WARM, E, kpk, b, held, feat[t], st, bp)
        if np.isnan(tg): tg = 0.0
        if tg > 3.0: tg = 3.0
        if tg < 0.0: tg = 0.0
        stp = step if (tg >= 1.0 or held >= 1.0) else fstep
        if abs(tg - held) >= stp or (tg == 0 and held > 0):
            held = np.round(tg / stp) * stp
        if t == WARM - 1:
            for j in range(delay): q[j] = held
        elif t >= WARM:
            q[delay - 1] = held
        if recon == 1 and t >= WARM:
            rec[t - WARM, 0] = E
    if mode == 0:
        unr = v0 - b0
        fin = E - due - tax * max(real + unr - D, 0.0)
    else:
        fin = E - taxf * max(real - D, 0.0)
    out[0] = fin; out[1] = emin; out[2] = mdd; out[3] = E7; out[4] = E12; out[5] = ntr; out[6] = taxp; out[7] = costp
    out[8] = E; out[9] = levsum / max(nk, 1.0); out[10] = nliq; out[11] = neg; out[12] = maxlev

@njit(parallel=True, cache=True)
def runPF(R, RF, B, FEAT, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
          mode, L3x, N0, cmode, s, fee, m, taxf, daily):
    P, T = R.shape; out = np.zeros((P, NO)); EE = np.zeros((P, T - WARM))
    for i in prange(P):
        rec = np.zeros((T - WARM, 1))
        run1F(R[i], RF[i], B[i], FEAT[i], delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
              mode, L3x, N0, cmode, s, fee, m, taxf, daily, out[i], rec, 1)
        EE[i] = rec[:, 0]
    return out, EE
