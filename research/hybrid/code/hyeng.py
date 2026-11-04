"""research/hybrid (thread '기존 매매법 장단점 합쳐 새로 만들기', 2026-11-04). Data <= 2014-12-31 only.

Dynamic-weight combination engine = D_EDGEMIX el._comb (one MS1 tax pot, average cost, 0.3%/side, 22% yearly on net realized
gain over D, no carry-forward, year-end harvest, FINAL LIQUIDATION TAX, cash = max(rf-2%,0)*(1-15.4%)) generalised so that the
s0.85 sleeve share A[p,k] and partner shares Wd[p,k,j] may change over time.
  - The s0.85 sleeve follows its standalone held level CU[p,k] exactly as in el._comb (TQQQ = level/3 of the sleeve, rest cash).
  - When the in-force targets (A, Wd) change on day k the whole account is traded to the new targets at close k (cost, realized
    gains booked). Targets passed in are IN FORCE (decision at close t is in force from k = t + delay; the caller shifts).
  - Every rbn days a band check (|w - target| > min(babs, brel*target)) rebalances drift, same as el._comb.
With constant A and Wd the result equals el._comb (checked in hy_parity.py).
Partner streams S/SO come from the I_INTEGRATE library (ii.arrays): path-consistent daily net returns and sold fractions.
"""
import os, sys, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/hybrid_nbcache')
from numba import njit, prange
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el, beng          # noqa: E402  (ii sets the D_EDGEMIX / std paths)

WARM = el.WARM
_K = dict(el.F1); PP, DED = beng._args(_K)


@njit(cache=True)
def _dyn1(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, NT):
    T = TQ.shape[1]; K = S.shape[2]
    v0 = 0.0; b0 = 0.0; v3 = 0.0; vc = 0.0
    vk = np.zeros(K); bk_ = np.zeros(K); Wc = np.zeros(K)
    real = 0.0; cur = -99.0; ac = 0.0; ntr = 0
    for k in range(T):
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = v0 + v3 + vc
                for j in range(K): tot += vk[j]
                f = min(due / max(tot, 1e-300), 1.0)
                real += f * (v0 - b0)
                v0 *= (1 - f); b0 *= (1 - f); v3 *= (1 - f); vc *= (1 - f)
                for j in range(K):
                    real += f * (vk[j] - bk_[j]); vk[j] *= (1 - f); bk_[j] *= (1 - f)
        if k > 0:
            v0 *= (1 + TQ[p, k]); v3 *= (1 + DEP[p, k]); vc *= (1 + DEP[p, k])
            for j in range(K):
                vk[j] *= (1 + S[p, k, j])
                fso = SO[p, k, j]
                if fso > 0:
                    real += fso * (vk[j] - bk_[j]); bk_[j] = bk_[j] * (1 - fso) + fso * vk[j]
        L = CU[p, k]
        if k == 0:
            ac = A[p, 0]; v3 = ac; vc = 1.0 - ac
            for j in range(K):
                Wc[j] = Wd[p, 0, j]; vc -= Wc[j]; vk[j] = Wc[j] * (1 - cost); bk_[j] = Wc[j]
        # s0.85 sleeve internal level change (exactly el._comb)
        if L != cur:
            tot = v0 + v3
            w0 = L / 3; t0 = w0 * tot; d0 = t0 - v0
            tc = cost * abs(d0)
            if d0 < 0 and v0 > 0:
                fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
            if d0 > 0: b0 += d0
            idle = (1 - w0) * tot
            sc = (tot - tc) / max(tot, 1e-300)
            v0 = t0 * sc; v3 = idle * sc
            cur = L
            if tc > 0: ntr += 1
        # target change or band check -> trade whole account to targets
        chg = False
        if k > 0:
            if abs(A[p, k] - ac) > 1e-12: chg = True
            for j in range(K):
                if abs(Wd[p, k, j] - Wc[j]) > 1e-12: chg = True
        go = chg
        if (not go) and k > 0 and k % rbn == 0:
            tot = v0 + v3 + vc
            for j in range(K): tot += vk[j]
            wr = (v0 + v3) / tot
            if ac > 0 and abs(wr - ac) > min(babs, brel * ac): go = True
            for j in range(K):
                if Wc[j] > 0 and abs(vk[j] / tot - Wc[j]) > min(babs, brel * Wc[j]): go = True
        if go and k > 0:
            ac = A[p, k]
            for j in range(K): Wc[j] = Wd[p, k, j]
            tot = v0 + v3 + vc
            for j in range(K): tot += vk[j]
            tc = 0.0
            tr = ac * tot; w0 = cur / 3; t0 = w0 * tr; d0 = t0 - v0
            tc += cost * abs(d0)
            if d0 < 0 and v0 > 0:
                fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
            if d0 > 0: b0 += d0
            v0 = t0; v3 = tr - t0
            rest = 1.0 - ac
            for j in range(K):
                tg = Wc[j] * tot; dj = tg - vk[j]
                tc += cost * abs(dj)
                if dj < 0 and vk[j] > 0:
                    fr = min(-dj / vk[j], 1.0); real += fr * (vk[j] - bk_[j]); bk_[j] *= 1 - fr
                if dj > 0: bk_[j] += dj
                vk[j] = tg; rest -= Wc[j]
            vc = rest * tot
            sc = (tot - tc) / tot
            v0 *= sc; v3 *= sc; vc *= sc
            for j in range(K): vk[j] *= sc
            if tc > 0: ntr += 1
        if harvest > 0 and k % 252 == 251:
            for q in range(K + 1):
                if q == 0:
                    v = v0; b = b0
                else:
                    v = vk[q - 1]; b = bk_[q - 1]
                if v <= 1e-12: continue
                target = D - real; U = v - b; f = 0.0
                if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                rz = f * U; sv = f * v
                if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                    tc = 2 * cost * sv; real += rz; b = b - (sv - rz) + (sv - tc); v -= tc
                    if q == 0:
                        v0 = v; b0 = b
                    else:
                        vk[q - 1] = v; bk_[q - 1] = b
        E = v0 + v3 + vc
        for j in range(K): E += vk[j]
        EE[p, k] = E
    unr = v0 - b0
    for j in range(K): unr += vk[j] - bk_[j]
    fin[p] = E - tax * max(real + unr - D, 0.0)
    NT[p] = ntr


@njit(parallel=True, cache=True)
def _dyn(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel):
    P, T = TQ.shape
    EE = np.zeros((P, T)); fin = np.zeros(P); NT = np.zeros(P)
    for p in prange(P):
        _dyn1(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, NT)
    return fin, EE, NT


def ref(bn):
    """TQ, DEP, CU (in force per scored day) for the standalone s0.85 on basis bn (same as el.ref_inputs)"""
    return ii.ref_in(bn)


def sid(name):
    return ii.SID.index(name)


def run(bn, A, Wd, names, cost=0.003, rbn=21, babs=0.05, brel=0.25, D=None, CUo=None):
    """A (P,T) or scalar s0.85 sleeve share; Wd (P,T,K) or (K,) partner shares for names (I_INTEGRATE stream ids, e.g. 'VALPROF4_L1').
    Returns fin (after final liquidation tax), E (P,T) after-tax-year equity curve, ntr (trades per path)."""
    TQ, DEP, CU, _ = ref(bn)
    if CUo is not None: CU = CUo
    S, SO = ii.arrays(bn)
    P, T = TQ.shape
    idx = [sid(n) for n in names]
    order = np.argsort(idx, kind='stable'); idx = [idx[i] for i in order]   # canonical SID order (harvest loop order = el._comb)
    if len(idx):
        Sa = np.ascontiguousarray(S[:, :, idx]).astype(np.float64); SOa = np.ascontiguousarray(SO[:, :, idx]).astype(np.float64)
    else:
        Sa = np.zeros((P, T, 0)); SOa = np.zeros((P, T, 0))
    if np.isscalar(A): A = np.full((P, T), float(A))
    Wd = np.asarray(Wd, dtype=np.float64)
    if Wd.ndim == 1: Wd = np.broadcast_to(Wd[None, None, :], (P, T, len(idx)))
    if len(idx): Wd = Wd[..., order]
    fin, EE, NT = _dyn(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), Sa, SOa,
                       np.ascontiguousarray(A, dtype=np.float64), np.ascontiguousarray(Wd), float(cost), PP['tax'],
                       DED if D is None else D, int(PP['harvest']), PP['hthr'], int(rbn), float(babs), float(brel))
    return fin, EE, NT


def cagr(fin, T):
    return np.maximum(fin, 1e-9) ** (252.0 / T) - 1


def stats(bn, fin, E, fref=None):
    r = ii.stats(bn, fin, E)
    if fref is not None:
        T = E.shape[1]; d = cagr(fin, T) - cagr(fref, T)
        r.update(d=float(np.median(d)), pw=float(np.mean(d > 1e-5)))
    return r


# ---------------------------------------------------------------- D1: CPPI / TIPP between the s0.85 sleeve and ONE safe partner
@njit(cache=True)
def _cppi1(TQ, DEP, CU, S, SO, m, f, cost, tax, D, harvest, hthr, rbn, babs, brel, delay, p, EE, fin, AA):
    """same accounting as _dyn1 with K = 1 partner; s0.85 share decided every rbn days at close k from the account's own
    after-tax-year equity: a = clip(m * (E - f*HWM) / E, 0, 1), in force from k + delay (traded at that close)."""
    T = TQ.shape[1]; K = 1
    v0 = 0.0; b0 = 0.0; v3 = 0.0; vc = 0.0
    vk = np.zeros(K); bk_ = np.zeros(K); Wc = np.zeros(K)
    real = 0.0; cur = -99.0; ac = 0.0; hwm = 1.0
    apl = np.full(T + delay + 1, -1.0)
    a0 = min(max(m * (1.0 - f), 0.0), 1.0)
    for k in range(T):
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = v0 + v3 + vc + vk[0]
                fr_ = min(due / max(tot, 1e-300), 1.0)
                real += fr_ * (v0 - b0) + fr_ * (vk[0] - bk_[0])
                v0 *= (1 - fr_); b0 *= (1 - fr_); v3 *= (1 - fr_); vc *= (1 - fr_); vk[0] *= (1 - fr_); bk_[0] *= (1 - fr_)
        if k > 0:
            v0 *= (1 + TQ[p, k]); v3 *= (1 + DEP[p, k]); vc *= (1 + DEP[p, k])
            vk[0] *= (1 + S[p, k, 0])
            fso = SO[p, k, 0]
            if fso > 0:
                real += fso * (vk[0] - bk_[0]); bk_[0] = bk_[0] * (1 - fso) + fso * vk[0]
        L = CU[p, k]
        if k == 0:
            ac = a0; v3 = ac; vc = 0.0
            Wc[0] = 1.0 - ac; vk[0] = Wc[0] * (1 - cost); bk_[0] = Wc[0]
        if L != cur:
            tot = v0 + v3
            w0 = L / 3; t0 = w0 * tot; d0 = t0 - v0
            tc = cost * abs(d0)
            if d0 < 0 and v0 > 0:
                fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
            if d0 > 0: b0 += d0
            idle = (1 - w0) * tot
            sc = (tot - tc) / max(tot, 1e-300)
            v0 = t0 * sc; v3 = idle * sc
            cur = L
        go = False; anew = ac
        if k > 0 and apl[k] >= 0 and abs(apl[k] - ac) > 1e-12:
            go = True; anew = apl[k]
        if (not go) and k > 0 and k % rbn == 0:
            tot = v0 + v3 + vc + vk[0]
            wr = (v0 + v3) / tot
            if ac > 0 and abs(wr - ac) > min(babs, brel * ac): go = True
            if Wc[0] > 0 and abs(vk[0] / tot - Wc[0]) > min(babs, brel * Wc[0]): go = True
        if go and k > 0:
            ac = anew; Wc[0] = 1.0 - ac
            tot = v0 + v3 + vc + vk[0]
            tc = 0.0
            tr = ac * tot; w0 = cur / 3; t0 = w0 * tr; d0 = t0 - v0
            tc += cost * abs(d0)
            if d0 < 0 and v0 > 0:
                fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
            if d0 > 0: b0 += d0
            v0 = t0; v3 = tr - t0
            tg = Wc[0] * tot; dj = tg - vk[0]
            tc += cost * abs(dj)
            if dj < 0 and vk[0] > 0:
                fr = min(-dj / vk[0], 1.0); real += fr * (vk[0] - bk_[0]); bk_[0] *= 1 - fr
            if dj > 0: bk_[0] += dj
            vk[0] = tg; vc = 0.0
            sc = (tot - tc) / tot
            v0 *= sc; v3 *= sc; vk[0] *= sc
        if harvest > 0 and k % 252 == 251:
            for q in range(2):
                if q == 0:
                    v = v0; b = b0
                else:
                    v = vk[0]; b = bk_[0]
                if v <= 1e-12: continue
                target = D - real; U = v - b; ff = 0.0
                if target < 0 and U < 0 and (harvest & 1): ff = min(1.0, target / U)
                if target > 0 and U > 0 and (harvest & 2): ff = min(1.0, target / U)
                rz = ff * U; sv = ff * v
                if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                    tc = 2 * cost * sv; real += rz; b = b - (sv - rz) + (sv - tc); v -= tc
                    if q == 0:
                        v0 = v; b0 = b
                    else:
                        vk[0] = v; bk_[0] = b
        E = v0 + v3 + vc + vk[0]
        EE[p, k] = E; AA[p, k] = ac
        if E > hwm: hwm = E
        if k % rbn == 0:
            cush = (E - f * hwm) / max(E, 1e-300)
            apl[k + delay] = min(max(m * cush, 0.0), 1.0)
    unr = (v0 - b0) + (vk[0] - bk_[0])
    fin[p] = E - tax * max(real + unr - D, 0.0)


@njit(parallel=True, cache=True)
def _cppi(TQ, DEP, CU, S, SO, m, f, cost, tax, D, harvest, hthr, rbn, babs, brel, delay):
    P, T = TQ.shape
    EE = np.zeros((P, T)); fin = np.zeros(P); AA = np.zeros((P, T))
    for p in prange(P):
        _cppi1(TQ, DEP, CU, S, SO, m, f, cost, tax, D, harvest, hthr, rbn, babs, brel, delay, p, EE, fin, AA)
    return fin, EE, AA


def run_cppi(bn, safe, m, f, cost=0.003, delay=2, CUo=None):
    TQ, DEP, CU, _ = ref(bn)
    if CUo is not None: CU = CUo
    S, SO = ii.arrays(bn); j = sid(safe)
    Sa = np.ascontiguousarray(S[:, :, j:j + 1]).astype(np.float64); SOa = np.ascontiguousarray(SO[:, :, j:j + 1]).astype(np.float64)
    return _cppi(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), Sa, SOa, float(m), float(f), float(cost),
                 PP['tax'], DED, int(PP['harvest']), PP['hthr'], 21, 0.05, 0.25, int(delay))
