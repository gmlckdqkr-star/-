"""copy of user_port_up upeng.run_port + per-product extra sell cost xsell (PTP withholding stress, ADDENDUM 1 P7)."""
import numpy as np
from numba import njit

@njit(cache=True)
def run_port_x(r, dg, do, Wt, tflag, ws, reb, band, notax, cost, tax, D, dtax, out, curve, xsell):
    """r, dg, do: (K, J) scored part. Wt: (S, K, J) in-force internal targets, tflag: (S, K) internal trade days (k=0 always).
    ws: (S,) sleeve weights. reb: (K,) calendar rebalance. band > 0: relative band (|w/ws - 1| > band at close k-2 -> rebalance k)."""
    K, NJ = r.shape; NS = ws.shape[0]
    v = np.zeros((NS, NJ)); b = np.zeros((NS, NJ)); cf = np.zeros(NJ); yg = np.zeros(NJ); yo = np.zeros(NJ)
    real = 0.0; gpk = 1.0; mdd = 0.0; ntr = 0.0; costp = 0.0; taxp = 0.0
    pend = np.zeros(K + 3, np.bool_)
    E7 = np.nan; E12 = np.nan
    for k in range(K):
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = v.sum(); f = min(due / max(tot, 1e-300), 1.0); taxp += due
                for s in range(NS):
                    for j in range(NJ):
                        if not notax[j]: real += f * (v[s, j] - b[s, j])
                        v[s, j] *= (1 - f); b[s, j] *= (1 - f)
        if k > 0:
            for s in range(NS):
                for j in range(NJ):
                    vb = v[s, j]; v[s, j] *= (1 + r[k, j])
                    if notax[j]: b[s, j] = v[s, j]
                    else:
                        yg[j] += vb * dg[k, j]; yo[j] += vb * do[k, j]
        # internal retarget
        for s in range(NS):
            if k == 0 or tflag[s, k]:
                tot = 0.0
                for j in range(NJ): tot += v[s, j]
                if k == 0: tot = ws[s]
                tc = 0.0
                for j in range(NJ):
                    d0 = Wt[s, k, j] * tot - v[s, j]
                    if notax[j]: continue
                    if d0 < 0 and v[s, j] > 0:
                        fr = min(-d0 / v[s, j], 1.0); real += fr * (v[s, j] - b[s, j]); b[s, j] *= 1 - fr
                        tc += xsell[j] * (-d0)
                    if d0 > 0: b[s, j] += d0
                    tc += cost * abs(d0)
                if tc > 0: ntr += 1
                costp += tc; sc = (tot - tc) / max(tot, 1e-300)
                for j in range(NJ):
                    v[s, j] = Wt[s, k, j] * tot * sc
                    if notax[j]: b[s, j] = v[s, j]
        # portfolio rebalance across sleeves
        if k > 0 and (reb[k] or pend[k]) and NS > 1:
            E = v.sum(); tc = 0.0
            for s in range(NS):
                Vs = 0.0
                for j in range(NJ): Vs += v[s, j]
                tgt = ws[s] * E
                for j in range(NJ):
                    p = v[s, j] / Vs if Vs > 1e-300 else Wt[s, k, j]
                    d0 = p * tgt - v[s, j]
                    if not notax[j]:
                        if d0 < 0 and v[s, j] > 0:
                            fr = min(-d0 / v[s, j], 1.0); real += fr * (v[s, j] - b[s, j]); b[s, j] *= 1 - fr
                            tc += xsell[j] * (-d0)
                        if d0 > 0: b[s, j] += d0
                        tc += cost * abs(d0)
                    v[s, j] += d0
                    if notax[j]: b[s, j] = v[s, j]
            costp += tc; sc = (E - tc) / max(E, 1e-300); ntr += 1
            for s in range(NS):
                for j in range(NJ):
                    v[s, j] *= sc
                    if notax[j]: b[s, j] = v[s, j]
        if k % 252 == 251:
            for j in range(NJ):
                if notax[j]: continue
                g = yg[j] - cf[j]
                if g > 0: d = g; cf[j] = 0.0
                else: d = 0.0; cf[j] = -g
                d += max(yo[j], 0.0)
                if d > 0:
                    tv = 0.0
                    for s in range(NS): tv += v[s, j]
                    if tv > 0:
                        d = min(d, tv)
                        for s in range(NS):
                            sh = d * v[s, j] / tv; v[s, j] -= dtax * sh; b[s, j] += (1 - dtax) * sh
                yg[j] = 0.0; yo[j] = 0.0
            target = D - real
            for s in range(NS):
                for j in range(NJ):
                    if notax[j] or v[s, j] <= 1e-12: continue
                    U = v[s, j] - b[s, j]; f = 0.0
                    if target < 0 and U < 0: f = min(1.0, target / U)
                    if target > 0 and U > 0: f = min(1.0, target / U)
                    rz = f * U; sv = f * v[s, j]
                    if sv > 0 and tax * abs(rz) > (2 * cost + xsell[j]) * sv:
                        tc = (2 * cost + xsell[j]) * sv; costp += tc; real += rz; target -= rz
                        b[s, j] = b[s, j] - (sv - rz) + (sv - tc); v[s, j] -= tc
        E = v.sum(); curve[k] = E
        gpk = max(gpk, E); mdd = min(mdd, E / gpk - 1)
        if k == 7 * 252 - 1: E7 = E
        if k == 12 * 252 - 1: E12 = E
        if band > 0 and NS > 1 and k + 2 < K:
            for s in range(NS):
                Vs = 0.0
                for j in range(NJ): Vs += v[s, j]
                if ws[s] > 0 and abs(Vs / E / ws[s] - 1) > band: pend[k + 2] = True
    unr = 0.0
    for s in range(NS):
        for j in range(NJ):
            if not notax[j]: unr += v[s, j] - b[s, j]
    E = v.sum()
    out[0] = E - tax * max(real + unr - D, 0.0); out[1] = mdd; out[2] = E7; out[3] = E12; out[4] = ntr; out[5] = costp; out[6] = taxp
