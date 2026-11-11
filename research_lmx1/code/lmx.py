"""LMX1 engine + runner (PRECOMMIT_LMX1.md sha ea90e616). <=2014 only.
_comb1f = el._comb1 copied verbatim except ONE change: a negative cash balance vc (borrowed money) accrues at FIN[p,k] instead of DEP[p,k].
Financing is not tax deductible (never touches `real`). a0=1, W=0 must reproduce v1 (parity)."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
from numba import njit, prange
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el
OUT = '/mnt/project-files/research/lmx1/results/'

@njit(cache=True)
def _comb1f(TQ, DEP, FIN, CU, IDL, S, SO, a0, W, a1, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin):
    T = TQ.shape[1]; K = S.shape[2]
    if True:
        v0 = 0.0; b0 = 0.0; v3 = 0.0; vt = 0.0; bt = 0.0; vc = 0.0
        vk = np.zeros(K); bk_ = np.zeros(K)
        real = 0.0; cur = -99.0
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
            if k > 0:
                v0 *= (1 + TQ[p, k]); v3 *= (1 + DEP[p, k]); vt *= (1 + IDL[p, k])
                if vc >= 0: vc *= (1 + DEP[p, k])          # LMX1 change (only this if/else)
                else: vc *= (1 + FIN[p, k])
                for j in range(K):
                    vk[j] *= (1 + S[p, k, j])
                    fso = SO[p, k, j]
                    if fso > 0:
                        real += fso * (vk[j] - bk_[j]); bk_[j] = bk_[j] * (1 - fso) + fso * vk[j]
            L = CU[p, k]
            if k == 0:
                v3 = a0; vc = 1.0 - a0
                for j in range(K):
                    vc -= W[j]; vk[j] = W[j] * (1 - cost); bk_[j] = W[j]
            if L != cur:
                tot = v0 + v3 + vt
                w0 = L / 3; t0 = w0 * tot; d0 = t0 - v0
                tc = cost * abs(d0)
                if d0 < 0 and v0 > 0:
                    fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                if d0 > 0: b0 += d0
                idle = (1 - w0) * tot
                vt_new = idle if (a1 == 1 and L < 1.0) else 0.0
                dt = vt_new - vt
                if a1 == 1 and abs(dt) > 1e-15:
                    tc += cost * abs(dt)
                    if dt < 0 and vt > 0:
                        fr = min(-dt / vt, 1.0); real += fr * (vt - bt); bt *= 1 - fr
                    if dt > 0: bt += dt
                sc = (tot - tc) / max(tot, 1e-300)
                v0 = t0 * sc; vt = vt_new * sc; v3 = (idle - vt_new) * sc
                cur = L
            if K > 0 and k > 0 and k % rbn == 0:
                tot = v0 + v3 + vt + vc
                for j in range(K): tot += vk[j]
                go = False
                wr = (v0 + v3 + vt) / tot
                if a0 > 0 and abs(wr - a0) > min(babs, brel * a0): go = True
                for j in range(K):
                    if W[j] > 0 and abs(vk[j] / tot - W[j]) > min(babs, brel * W[j]): go = True
                if go:
                    tc = 0.0
                    tr = a0 * tot; w0 = cur / 3; t0 = w0 * tr; d0 = t0 - v0
                    tc += cost * abs(d0)
                    if d0 < 0 and v0 > 0:
                        fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                    if d0 > 0: b0 += d0
                    idle = tr - t0
                    vt_new = idle if (a1 == 1 and cur < 1.0) else 0.0
                    dt = vt_new - vt
                    if abs(dt) > 1e-15:
                        tc += cost * abs(dt)
                        if dt < 0 and vt > 0:
                            fr = min(-dt / vt, 1.0); real += fr * (vt - bt); bt *= 1 - fr
                        if dt > 0: bt += dt
                    v0 = t0; vt = vt_new; v3 = idle - vt_new
                    rest = 1.0 - a0
                    for j in range(K):
                        tg = W[j] * tot; dj = tg - vk[j]
                        tc += cost * abs(dj)
                        if dj < 0 and vk[j] > 0:
                            fr = min(-dj / vk[j], 1.0); real += fr * (vk[j] - bk_[j]); bk_[j] *= 1 - fr
                        if dj > 0: bk_[j] += dj
                        vk[j] = tg; rest -= W[j]
                    vc = rest * tot
                    sc = (tot - tc) / tot
                    v0 *= sc; vt *= sc; v3 *= sc; vc *= sc
                    for j in range(K): vk[j] *= sc
            if harvest > 0 and k % 252 == 251:
                for q in range(K + 2):
                    if q == 0:
                        v = v0; b = b0
                    elif q == 1:
                        v = vt; b = bt
                    else:
                        v = vk[q - 2]; b = bk_[q - 2]
                    if v <= 1e-12: continue
                    target = D - real; U = v - b; f = 0.0
                    if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                    if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                    rz = f * U; sv = f * v
                    if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                        tc = 2 * cost * sv; real += rz; b = b - (sv - rz) + (sv - tc); v -= tc
                        if q == 0:
                            v0 = v; b0 = b
                        elif q == 1:
                            vt = v; bt = b
                        else:
                            vk[q - 2] = v; bk_[q - 2] = b
            E = v0 + v3 + vt + vc
            for j in range(K): E += vk[j]
            EE[p, k] = E
        unr = (v0 - b0) + (vt - bt)
        for j in range(K): unr += vk[j] - bk_[j]
        fin[p] = E - tax * max(real + unr - D, 0.0)

@njit(parallel=True, cache=True)
def _combf(TQ, DEP, FIN, CU, IDL, S, SO, a0, W, a1, cost, tax, D, harvest, hthr, rbn, babs, brel):
    P, T = TQ.shape
    EE = np.zeros((P, T)); fin = np.zeros(P)
    for p in prange(P):
        _comb1f(TQ, DEP, FIN, CU, IDL, S, SO, a0, W, a1, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin)
    return fin, EE

BASES = ['real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'dev250_path']
ER3 = el.ER3
def fin_rate(bn, mode, s=0.004):
    """daily financing rate on borrowed money. mode U: rf + 0.4%. R: phi(L) i_f=0. Ri: phi(L) with i_f = DEP."""
    TQ, DEP, CU, IDL = ii.ref_in(bn); rf = np.asarray(el.ctx(bn)['rf'])[:, ii.WARM:].astype(np.float64)
    if mode == 'U': return rf + 0.004 / 252
    Lp = np.roll(CU, 1, axis=1); Lp[:, 0] = CU[:, 0]; g = Lp / 3.0          # level held during day k = level set at k-1
    phi = 2.5 * g * (rf + 3 * s / 252 - ER3 / 252) + 2.5 * (1 - g) * DEP
    if mode == 'Ri': phi = phi - 1.5 * DEP
    return phi

def sleeves(bn, extra_drag=0.0):
    S, SO = ii.arrays(bn); jv = ii.SID.index('VALPROF4_L1'); jc = ii.SID.index('CAPE_L3')
    v = S[:, :, jv].astype(np.float64) - 0.006 / 252 - extra_drag / 252; c = S[:, :, jc].astype(np.float64) - extra_drag / 252
    A = np.stack([v, c], 2); B = np.stack([SO[:, :, jv], SO[:, :, jc]], 2).astype(np.float64)
    return A, B

def run(bn, w, mode, s=0.004, extra_drag=0.0):
    TQ, DEP, CU, IDL = ii.ref_in(bn); A, B = sleeves(bn, extra_drag); w = np.asarray(w, float); act = np.where(w > 1e-9)[0]
    if len(act) == 0: Sa = np.zeros(A.shape[:2] + (1,)); SOa = np.zeros_like(Sa); wa = np.zeros(1)
    else: Sa = np.ascontiguousarray(A[:, :, act]); SOa = np.ascontiguousarray(B[:, :, act]); wa = np.ascontiguousarray(w[act])
    FIN = np.ascontiguousarray(fin_rate(bn, mode, s))
    return _combf(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), FIN, np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                  1.0, wa, 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)

def halves(E, Eref):
    """real NDX 1986-2014 split at 2000-01-03: sub-period CAGR difference (curves after yearly tax, before final liquidation tax)"""
    d = el.c_X('real_ndx_86_14').index[-E.shape[1]:]; k = int(np.searchsorted(d.values, np.datetime64('2000-01-03')))
    def g(e, a, b): return (e[b] / e[a]) ** (252.0 / (b - a)) - 1
    T = E.shape[1] - 1
    return dict(d_86_99=float(g(E[0], 0, k) - g(Eref[0], 0, k)), d_00_14=float(g(E[0], k, T) - g(Eref[0], k, T)),
                v1_86_99=float(g(Eref[0], 0, k)), v1_00_14=float(g(Eref[0], k, T)), split=str(d[k].date()))

TESTS = {'T1_V002x4/3': [0.20, 0.1333333333], 'T2_VP4_20': [0.20, 0.0], 'T3_VP4_30': [0.30, 0.0]}
ROWS = {'U': dict(mode='U'), 'R': dict(mode='R', s=0.004), 'Rs': dict(mode='R', s=0.008, extra_drag=0.01), 'Ri': dict(mode='Ri', s=0.004)}

if __name__ == '__main__':
    t0 = time.time(); out = {'parity': {}, 'tests': {}}
    REF = {}
    for bn in BASES:
        fin, E = run(bn, [0, 0], 'R'); r = ii.stats(bn, fin, E); REF[bn] = (fin, E)
        out['parity'][bn] = {k: float(r[k]) for k in ('cagr', 'mdd', 'dd80', 'dd95', 'd') if k in r}
        print('PARITY', bn, {k: round(v, 5) for k, v in out['parity'][bn].items()}, flush=True)
    for tn, w in TESTS.items():
        for rn, kw in ROWS.items():
            rec = {}
            for bn in BASES:
                fin, E = run(bn, w, **kw); r = ii.stats(bn, fin, E)
                rec[bn] = {k: float(r[k]) for k in ('cagr', 'mdd', 'p10', 'dd80', 'dd95', 'd', 'pw') if k in r}
                if bn == 'real_ndx_86_14': rec['halves'] = halves(E, REF[bn][1])
            out['tests'][tn + '|' + rn] = rec
            p = rec['dev250_path']; n = rec['real_ndx_86_14']; h = rec['halves']
            print('%-12s %-2s path %.4f (d %+.4f pw %.2f dd80 %.2f dd95 %.3f) realNDX %.4f (d %+.4f; 86-99 %+.4f, 00-14 %+.4f) spx55 %+.4f spx70 %+.4f' % (
                tn, rn, p['cagr'], p['d'], p['pw'], p['dd80'], p['dd95'], n['cagr'], n['d'], h['d_86_99'], h['d_00_14'],
                rec['real_spx_55_85']['d'], rec['real_spx_70_85']['d']), flush=True)
    json.dump(out, open(OUT + 'lmx1.json', 'w'), indent=1)
    print('done %.0fs' % (time.time() - t0))
