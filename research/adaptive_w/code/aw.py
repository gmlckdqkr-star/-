"""ADAPTIVE WEIGHTS engine (lane AW, 2026-11-05). Data <= 2014-12-31 only.
Copy of D_EDGEMIX el._comb1 (MS1 rules: one tax pot, 22% yearly tax with deduction, final liquidation tax, 0.3% one-way cost,
21-day band rebalancing) with TIME-VARYING target weights over (v1, sleeve1, sleeve2, ...).
Targets are updated every rbn days from each sleeve's own past returns, read with a `lag`-day delay (no look-ahead).
Rules (rid): 0 fixed | 1 TILT | 2 HEDGE | 3 BAYES | 4 DRIFT. Common guard: per-month move cap `spd`, floors LO, caps HI, sum = 1.
"""
import os, sys, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/AW/nbcache')
from numba import njit, prange

@njit(cache=True)
def _proj(w, LO, HI):
    n = w.shape[0]
    for j in range(n): w[j] = min(max(w[j], LO[j]), HI[j])
    for it in range(30):
        s = 0.0
        for j in range(n): s += w[j]
        d = 1.0 - s
        if abs(d) < 1e-12: break
        room = 0.0
        for j in range(n):
            room += (HI[j] - w[j]) if d > 0 else (w[j] - LO[j])
        if room <= 1e-15: break
        for j in range(n):
            r = (HI[j] - w[j]) if d > 0 else (w[j] - LO[j])
            w[j] += d * r / room
        for j in range(n): w[j] = min(max(w[j], LO[j]), HI[j])
    return w

@njit(cache=True)
def _rule(rid, prm, m, BM, W0, wcur, q):
    """BM[0..m]: cumulative log index per sleeve at decision times (lagged). returns raw target (before speed cap/clamp)."""
    n = W0.shape[0]; out = wcur.copy()
    if rid == 0: return W0.copy()
    if rid != 2 and m < 12: return out
    if rid == 1:                       # TILT: shrunk trailing L-month annualized log growth vs portfolio; prm = L, eta, n0
        L = int(prm[0]); eta = prm[1]; n0 = prm[2]
        nn = min(m, L); g = np.zeros(n); pm = 0.0
        for j in range(n):
            g[j] = (BM[m, j] - BM[m - nn, j]) / nn * 12.0 * nn / (nn + n0); pm += W0[j] * g[j]
        s = 0.0
        for j in range(n): out[j] = W0[j] * np.exp(eta * (g[j] - pm)); s += out[j]
        for j in range(n): out[j] /= s
        return out
    if rid == 2:                       # HEDGE (multiplicative weights + fixed share back to W0); prm = eta, alpha
        eta = prm[0]; al = prm[1]; s = 0.0
        for j in range(n): q[j] = q[j] * np.exp(eta * (BM[m, j] - BM[m - 1, j])); s += q[j]
        for j in range(n): q[j] = (1 - al) * q[j] / s + al * W0[j]
        for j in range(n): out[j] = q[j]
        return out
    if rid == 3:                       # BAYES: posterior mean of annual log edge vs portfolio, prior N(0,tau^2), expanding; prm = kappa, tau
        ka = prm[0]; tau = prm[1]
        d = np.zeros(m)
        s = 0.0
        for j in range(n):
            for t in range(m):
                xp = 0.0
                for i in range(n): xp += W0[i] * (BM[t + 1, i] - BM[t, i])
                d[t] = (BM[t + 1, j] - BM[t, j]) - xp
            mu = 0.0
            for t in range(m): mu += d[t]
            mu /= m
            v = 0.0
            for t in range(m): v += (d[t] - mu) ** 2
            v /= max(m - 1, 1)
            mua = mu * 12.0; va = v * 144.0 / m
            post = mua * tau * tau / (tau * tau + va)
            out[j] = W0[j] * np.exp(ka * post); s += out[j]
        for j in range(n): out[j] /= s
        return out
    if rid == 4:                       # DRIFT: best trailing-L sleeve +delta, worst -delta if gap > h; prm = delta, L, h
        de = prm[0]; L = int(prm[1]); h = prm[2]
        nn = min(m, L); b = 0; wv = 0; gb = -1e9; gw = 1e9
        for j in range(n):
            g = (BM[m, j] - BM[m - nn, j]) / nn * 12.0
            if g > gb: gb = g; b = j
            if g < gw: gw = g; wv = j
        if gb - gw > h:
            out[b] += de; out[wv] -= de
        return out
    return out

@njit(cache=True)
def _comb1(TQ, DEP, CU, IDL, S, SO, W0, LO, HI, rid, prm, spd, lag, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, WT):
    T = TQ.shape[1]; K = S.shape[2]; n = K + 1
    v0 = 0.0; b0 = 0.0; v3 = 0.0; vt = 0.0; bt = 0.0; vc = 0.0
    vk = np.zeros(K); bk_ = np.zeros(K)
    real = 0.0; cur = -99.0
    CL = np.zeros((T, n)); BM = np.zeros((T // rbn + 2, n))
    w = W0.copy(); q = W0.copy()
    a1 = 0
    for k in range(T):
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = v0 + v3 + vt + vc
                for j in range(K): tot += vk[j]
                f = min(due / max(tot, 1e-300), 1.0)
                real += f * (v0 - b0) + f * (vt - bt)
                v0 *= (1 - f); b0 *= (1 - f); v3 *= (1 - f); vt *= (1 - f); bt *= (1 - f); vc *= (1 - f)
                for j in range(K):
                    real += f * (vk[j] - bk_[j]); vk[j] *= (1 - f); bk_[j] *= (1 - f)
        pre = v0 + v3 + vt
        if k > 0:
            v0 *= (1 + TQ[p, k]); v3 *= (1 + DEP[p, k]); vt *= (1 + IDL[p, k]); vc *= (1 + DEP[p, k])
            for j in range(K):
                vk[j] *= (1 + S[p, k, j])
                fso = SO[p, k, j]
                if fso > 0:
                    real += fso * (vk[j] - bk_[j]); bk_[j] = bk_[j] * (1 - fso) + fso * vk[j]
        L = CU[p, k]
        if k == 0:
            v3 = W0[0]; vc = 1.0 - W0[0]
            for j in range(K):
                vc -= W0[j + 1]; vk[j] = W0[j + 1] * (1 - cost); bk_[j] = W0[j + 1]
        if L != cur:
            tot = v0 + v3 + vt
            w0 = L / 3; t0 = w0 * tot; d0 = t0 - v0
            tc = cost * abs(d0)
            if d0 < 0 and v0 > 0:
                fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
            if d0 > 0: b0 += d0
            idle = (1 - w0) * tot
            sc = (tot - tc) / max(tot, 1e-300)
            v0 = t0 * sc; vt = 0.0; v3 = idle * sc
            cur = L
        # sleeve unit indices (v1 incl. its own level-change cost; sleeves net of own costs)
        if k > 0:
            CL[k, 0] = CL[k - 1, 0] + np.log(max(v0 + v3 + vt, 1e-300) / max(pre, 1e-300))
            for j in range(K): CL[k, j + 1] = CL[k - 1, j + 1] + np.log1p(S[p, k, j])
        if k > 0 and k % rbn == 0:
            m = k // rbn; kk = max(k - lag, 0)
            for j in range(n): BM[m, j] = CL[kk, j]
            if rid > 0:
                raw = _rule(rid, prm, m, BM, W0, w, q)
                for j in range(n):
                    dj = raw[j] - w[j]
                    if rid != 4: dj = min(max(dj, -spd), spd)
                    raw[j] = w[j] + dj
                w = _proj(raw, LO, HI)
                if rid == 2:
                    for j in range(n): q[j] = min(max(q[j], LO[j]), HI[j])
            tot = v0 + v3 + vt + vc
            for j in range(K): tot += vk[j]
            go = False
            wr = (v0 + v3 + vt) / tot
            if w[0] > 0 and abs(wr - w[0]) > min(babs, brel * w[0]): go = True
            for j in range(K):
                if w[j + 1] > 0 and abs(vk[j] / tot - w[j + 1]) > min(babs, brel * w[j + 1]): go = True
            if go:
                tc = 0.0
                tr = w[0] * tot; w0 = cur / 3; t0 = w0 * tr; d0 = t0 - v0
                tc += cost * abs(d0)
                if d0 < 0 and v0 > 0:
                    fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                if d0 > 0: b0 += d0
                idle = tr - t0
                v0 = t0; vt = 0.0; v3 = idle
                rest = 1.0 - w[0]
                for j in range(K):
                    tg = w[j + 1] * tot; dj = tg - vk[j]
                    tc += cost * abs(dj)
                    if dj < 0 and vk[j] > 0:
                        fr = min(-dj / vk[j], 1.0); real += fr * (vk[j] - bk_[j]); bk_[j] *= 1 - fr
                    if dj > 0: bk_[j] += dj
                    vk[j] = tg; rest -= w[j + 1]
                vc = rest * tot
                sc = (tot - tc) / tot
                v0 *= sc; vt *= sc; v3 *= sc; vc *= sc
                for j in range(K): vk[j] *= sc
            for j in range(n): WT[p, m, j] = w[j]
        if harvest > 0 and k % 252 == 251:
            for qq in range(K + 2):
                if qq == 0:
                    v = v0; b = b0
                elif qq == 1:
                    v = vt; b = bt
                else:
                    v = vk[qq - 2]; b = bk_[qq - 2]
                if v <= 1e-12: continue
                target = D - real; U = v - b; f = 0.0
                if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                rz = f * U; sv = f * v
                if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                    tc = 2 * cost * sv; real += rz; b = b - (sv - rz) + (sv - tc); v -= tc
                    if qq == 0:
                        v0 = v; b0 = b
                    elif qq == 1:
                        vt = v; bt = b
                    else:
                        vk[qq - 2] = v; bk_[qq - 2] = b
        E = v0 + v3 + vt + vc
        for j in range(K): E += vk[j]
        EE[p, k] = E
    unr = (v0 - b0) + (vt - bt)
    for j in range(K): unr += vk[j] - bk_[j]
    fin[p] = E - tax * max(real + unr - D, 0.0)

@njit(parallel=True, cache=True)
def _comb(TQ, DEP, CU, IDL, S, SO, W0, LO, HI, rid, prm, spd, lag, cost, tax, D, harvest, hthr, rbn, babs, brel):
    P, T = TQ.shape
    EE = np.zeros((P, T)); fin = np.zeros(P); WT = np.zeros((P, T // rbn + 2, W0.shape[0]))
    for p in prange(P):
        _comb1(TQ, DEP, CU, IDL, S, SO, W0, LO, HI, rid, prm, spd, lag, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, WT)
    return fin, EE, WT

def bounds(W0, cap='A'):
    W0 = np.asarray(W0, float); LO = np.maximum(0.5 * W0, 0.0)
    if cap == 'A': HI = np.minimum(np.minimum(2 * W0, W0 + 0.25), 0.80)
    else: HI = np.minimum(W0 + 0.40, 0.80)
    HI = np.maximum(HI, W0)
    return LO, HI
