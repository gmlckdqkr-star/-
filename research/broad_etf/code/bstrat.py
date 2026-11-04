"""BE1 strategy builders (PRECOMMIT_BE1.md). All decisions at path row t use rows <= t only; in force from row t+delay."""
import numpy as np
import be1eng as G
WARM = G.WARM

def _expand(dec, K, NJ, delay, cash_j=-1):
    """dec: list of (t, Wd (P,NJ)) -> function p -> (W (K,NJ), flag (K,)); rows before the first decision is in force = CASH
    (fix 11-04: with delay 3 the first decision lands at k=1 and k=0 had all-zero targets, which wiped that sleeve)"""
    ks = [t + delay - WARM for t, _ in dec]
    def f(p):
        W = np.zeros((K, NJ)); W[:, cash_j] = 1.0; fl = np.zeros(K, bool)
        for i, (t, Wd) in enumerate(dec):
            a = max(ks[i], 0); bnd = ks[i + 1] if i + 1 < len(dec) else K
            if bnd <= 0 or a >= K: continue
            W[a:min(bnd, K)] = Wd[p]; fl[a] = True
        fl[0] = True; return W, fl
    return f

def _ctx(b):
    if 'LL' not in b:
        b['LL'], b['NB'] = G._cum(b['A'])
        b['LC'] = np.cumsum(np.log1p(np.maximum(b['rf'], 0)), axis=1)
    return b['LL'], b['NB'], b['LC']

def topk_dec(b, J, cand, k, L, t, absf=True):
    LL, NB, LC = _ctx(b); names = b['names']; P = LL.shape[0]; NJ = len(J)
    S = G.mom_score(LL, NB, t)
    idx = [names.index(n) for n in cand]
    Sc = S[:, idx]; r252 = G.window_ret(LL, NB, t, 252)[:, idx]; c252 = (LC[:, t] - LC[:, t - 252])[:, None]
    Wd = np.zeros((P, NJ))
    Sc2 = np.where(np.isfinite(Sc), Sc, -np.inf)
    order = np.argsort(-Sc2, axis=1)[:, :k]
    for p in range(P):
        for q in order[p]:
            if not np.isfinite(Sc2[p, q]): Wd[p, J[('CASH', 0)]] += 1.0 / k; continue
            if absf and not (r252[p, q] > c252[p, 0]): Wd[p, J[('CASH', 0)]] += 1.0 / k; continue
            Wd[p, J[(cand[q], L)]] += 1.0 / k
    return Wd

def F1(b, k, L, delay=2):
    prods, notax, J, mk = G.products(b, levs=(L,))
    T = b['A'].shape[1]; K = T - WARM
    cand = [n for n in b['names'] if n != 'SHY']
    dec = [(t, topk_dec(b, J, cand, k, L, t)) for t in G.decision_rows(T)]
    return (prods, notax, mk), [_expand(dec, K, len(J), delay)], (1.0,)

def F2(b, bn, S, k, delay=2):
    prods, notax, J, mk = G.products(b, levs=(1,), with_tqqq=True)
    T = b['A'].shape[1]; K = T - WARM; NJ = len(J)
    lv = G.s085_levels(bn, delay)
    cand = [n for n in (b['names'] if S == 'all' else ['TLT', 'IEF', 'GLD', 'XLU', 'XLP', 'XLV']) if n in b['names']]
    dec = [(t, topk_dec(b, J, cand, k, 1, t)) for t in G.decision_rows(T)]
    fill = _expand(dec, K, NJ, delay)
    def f(p):
        Wf, flf = fill(p); l = lv[p]; W = Wf * (1 - l / 3)[:, None]; W[:, J[('TQQQ', 3)]] += l / 3
        fl = flf | np.r_[True, np.diff(l) != 0]; return W, fl
    return (prods, notax, mk), [f], (1.0,)

def rp_dec(b, J, cand, sig, t):
    LL, NB, LC = _ctx(b); A = b['A']; names = b['names']; P = LL.shape[0]; NJ = len(J)
    idx = [names.index(n) for n in cand]
    lev = np.exp(LL[:, t - 199:t + 1][:, :, idx]); okw = (NB[:, t] - NB[:, t - 200])[:, idx] == 0
    on = okw & (lev[:, -1, :] > lev.mean(axis=1))
    R = A[:, t - 62:t + 1][:, :, idx]; vol = np.nanstd(R, axis=1) * 252 ** .5
    okv = np.isfinite(R).all(axis=1) & (vol > 1e-6)
    on = on & okv
    w = np.where(on, 1.0 / np.where(okv, vol, 1.0), 0.0); sw = w.sum(1, keepdims=True)
    w = np.where(sw > 0, w / np.maximum(sw, 1e-12), 0.0)
    pr = np.einsum('ptn,pn->pt', np.nan_to_num(R), w); sp = pr.std(1) * 252 ** .5
    s = np.where(sp > 1e-6, sig / np.maximum(sp, 1e-6), 0.0); s = np.minimum(s, 3.0)
    Wd = np.zeros((P, NJ))
    for p in range(P):
        if sw[p, 0] <= 0: Wd[p, J[('CASH', 0)]] = 1.0; continue
        if s[p] <= 1:
            for q, n in enumerate(cand): Wd[p, J[(n, 1)]] += w[p, q] * s[p]
            Wd[p, J[('CASH', 0)]] += 1 - s[p]
        else:
            bb = (s[p] - 1) / 2
            for q, n in enumerate(cand): Wd[p, J[(n, 1)]] += w[p, q] * (1 - bb); Wd[p, J[(n, 3)]] += w[p, q] * bb
    return Wd

def _rp_sleeve(b, J, sig, K, T, delay):
    cand = [n for n in b['names'] if n != 'SHY']
    dec = [(t, rp_dec(b, J, cand, sig, t)) for t in G.decision_rows(T)]
    return _expand(dec, K, len(J), delay)

def F3(b, bn, w, sig, delay=2):
    prods, notax, J, mk = G.products(b, levs=(1, 3), with_tqqq=True)
    T = b['A'].shape[1]; K = T - WARM; NJ = len(J); lv = G.s085_levels(bn, delay)
    def s0(p):
        W = np.zeros((K, NJ)); l = lv[p]; W[:, J[('TQQQ', 3)]] = l / 3; W[:, J[('CASH', 0)]] = 1 - l / 3
        return W, np.r_[True, np.diff(l) != 0]
    return (prods, notax, mk), [s0, _rp_sleeve(b, J, sig, K, T, delay)], (w, 1 - w)

def F4(b, sig, delay=2):
    prods, notax, J, mk = G.products(b, levs=(1, 3))
    T = b['A'].shape[1]; K = T - WARM
    return (prods, notax, mk), [_rp_sleeve(b, J, sig, K, T, delay)], (1.0,)

def S085(b, bn, delay=2):
    prods, notax, J, mk = G.products(b, levs=(1,), with_tqqq=True)
    T = b['A'].shape[1]; K = T - WARM; NJ = len(J); lv = G.s085_levels(bn, delay)
    def s0(p):
        W = np.zeros((K, NJ)); l = lv[p]; W[:, J[('TQQQ', 3)]] = l / 3; W[:, J[('CASH', 0)]] = 1 - l / 3
        return W, np.r_[True, np.diff(l) != 0]
    return (prods, notax, mk), [s0], (1.0,)

def runspec(b, spec, cost=0.003):
    (prods, notax, mk), sl, ws = spec
    fn = lambda p: [s(p) for s in sl]
    return G.run(b, fn, prods, notax, mk, ws=ws, cost=cost)
