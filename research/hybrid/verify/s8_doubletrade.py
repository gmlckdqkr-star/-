"""Verifier step 8 (check D/A timing): cost of the band check that fires at k % 21 == 0 two days BEFORE the new targets (decided at
close k) are traded at k + 2. Own copy of hyeng._dyn1 with one switch: skip the band check when the in-force target changes within the
next `dl` days (known at close k, because that target was decided at close k). skip=0 must reproduce H.run exactly."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np
from numba import njit, prange
import hyeng as H, hy_struct as HS, ii


@njit(cache=True)
def _dyn1s(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, NT, skip, dl):
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
        chg = False
        if k > 0:
            if abs(A[p, k] - ac) > 1e-12: chg = True
            for j in range(K):
                if abs(Wd[p, k, j] - Wc[j]) > 1e-12: chg = True
        go = chg
        pend = False
        if skip == 1:
            for q in range(k + 1, min(k + dl + 1, T)):
                if abs(A[p, q] - ac) > 1e-12: pend = True
                for j in range(K):
                    if abs(Wd[p, q, j] - Wc[j]) > 1e-12: pend = True
        if (not go) and (not pend) and k > 0 and k % rbn == 0:
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
def _dyns(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel, skip, dl):
    P, T = TQ.shape
    EE = np.zeros((P, T)); fin = np.zeros(P); NT = np.zeros(P)
    for p in prange(P):
        _dyn1s(TQ, DEP, CU, S, SO, A, Wd, cost, tax, D, harvest, hthr, rbn, babs, brel, p, EE, fin, NT, skip, dl)
    return fin, EE, NT


def run_s(bn, A, Wd, names, skip):
    TQ, DEP, CU, _ = H.ref(bn); S, SO = ii.arrays(bn)
    idx = [H.sid(n) for n in names]; order = np.argsort(idx, kind='stable'); idx = [idx[i] for i in order]
    Sa = np.ascontiguousarray(S[:, :, idx]).astype(np.float64); SOa = np.ascontiguousarray(SO[:, :, idx]).astype(np.float64)
    Wd = np.ascontiguousarray(np.asarray(Wd, dtype=np.float64)[..., order])
    return _dyns(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), Sa, SOa, np.ascontiguousarray(A, dtype=np.float64),
                 Wd, 0.003, H.PP['tax'], H.DED, int(H.PP['harvest']), H.PP['hthr'], 21, 0.05, 0.25, int(skip), 2)


for bn in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['real_ndx_86_14']):
    t0 = time.time()
    T = H.ref(bn)[0].shape[1]
    fref, _, _ = H.run(bn, 1.0, np.zeros(0), [])
    cr = H.cagr(fref, T)
    A, Wd, _ = HS.invvol_targets(bn)
    f_h, E_h, N_h = H.run(bn, A, Wd, HS.D2N)
    f0, E0, N0 = run_s(bn, A, Wd, HS.D2N, 0)
    f1, E1, N1 = run_s(bn, A, Wd, HS.D2N, 1)
    print(bn, 'D2: copy(skip=0) vs H.run max|log fin diff| %.2e' % np.max(np.abs(np.log(f0) - np.log(f_h))))
    print('   D2 cagr median: as run %.4f  | skip band check when a new target is 1-2 days away %.4f ; d_pair %.4f -> %.4f ; trades/yr %.1f -> %.1f' % (
        np.median(H.cagr(f0, T)), np.median(H.cagr(f1, T)), np.median(H.cagr(f0, T) - cr), np.median(H.cagr(f1, T) - cr),
        np.median(N0) / (T / 252), np.median(N1) / (T / 252)))
    for nm, (m, f) in {'D1a': (3.0, 0.6), 'D1b': (2.0, 0.7)}.items():
        fc, Ec, AA = H.run_cppi(bn, 'BOND10_L1', m, f)
        g0, _, n0 = run_s(bn, AA, (1 - AA)[:, :, None], ['BOND10_L1'], 0)
        g1, _, n1 = run_s(bn, AA, (1 - AA)[:, :, None], ['BOND10_L1'], 1)
        print('   %s replay (fixed AA): cagr %.4f -> %.4f without the pre-decision band trade ; trades/yr %.1f -> %.1f' % (
            nm, np.median(H.cagr(g0, T)), np.median(H.cagr(g1, T)), np.median(n0) / (T / 252), np.median(n1) / (T / 252)))
    print('   %.1f s' % (time.time() - t0), flush=True)
