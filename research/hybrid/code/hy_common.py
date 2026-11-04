"""Shared helpers for research/hybrid (<=2014 only). Block grid, sleeve return arrays, engine call on tiled arrays."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hyeng as H, ii   # noqa

BLK = 21
DELAY = 2


def sleeve_returns(bn, names):
    """daily pre-tax net returns (P, T, 1+K): column 0 = s0.85 sleeve ((CU_{k-1}/3) TQ_k + (1 - CU_{k-1}/3) DEP_k), then partners"""
    TQ, DEP, CU, _ = H.ref(bn); S, _ = ii.arrays(bn)
    Lp = np.concatenate([CU[:, :1], CU[:, :-1]], axis=1) / 3.0
    rs = Lp * TQ + (1 - Lp) * DEP; rs[:, 0] = 0.0
    cols = [rs] + [S[:, :, H.sid(n)].astype(np.float64) for n in names]
    return np.stack(cols, axis=2)


def block_starts(T, k0=0):
    return np.arange(k0, T - 3, BLK)


def block_logsum(R):
    """R (P,T,M) daily returns -> function(k) giving (P,M) log sums over days k+3..k+23 (truncated at T-1)"""
    lr = np.log1p(np.maximum(R, -0.999999))
    cs = np.concatenate([np.zeros(lr.shape[:1] + (1,) + lr.shape[2:]), np.cumsum(lr, axis=1)], axis=1)
    T = R.shape[1]
    def f(k):
        a = min(k + 3, T); b = min(k + 24, T)
        return cs[:, b] - cs[:, a]
    return f, cs


def inforce_from_picks(picks, T, M, ks):
    """picks (P, nb) index 0..M-1 decided at block starts ks -> A (P,T), Wd (P,T,M-1) in force from k+DELAY until next in-force"""
    P = picks.shape[0]
    A = np.zeros((P, T)); Wd = np.zeros((P, T, M - 1))
    for i, k in enumerate(ks):
        a = 0 if i == 0 else k + DELAY
        b = T if i == len(ks) - 1 else ks[i + 1] + DELAY
        a = min(a, T); b = min(b, T)
        if a >= b: continue
        pk = picks[:, i]
        A[:, a:b] = (pk == 0)[:, None]
        for j in range(1, M):
            Wd[:, a:b, j - 1] = (pk == j)[:, None]
    return A, Wd


def run_tiled(bn, names, A, Wd, cost=0.003, CUo=None):
    """engine on basis bn with A (Q,T), Wd (Q,T,K); if the basis has P=1 and Q>1 the path arrays are tiled Q times"""
    TQ, DEP, CU, _ = H.ref(bn); S, SO = ii.arrays(bn)
    if CUo is not None: CU = CUo
    P, T = TQ.shape; Q = A.shape[0]
    idx = [H.sid(n) for n in names]; order = np.argsort(idx, kind='stable'); idx = [idx[i] for i in order]
    Sa = S[:, :, idx].astype(np.float64); SOa = SO[:, :, idx].astype(np.float64)
    Wd = Wd[..., order]
    if P == 1 and Q > 1:
        TQ = np.repeat(TQ, Q, 0); DEP = np.repeat(DEP, Q, 0); CU = np.repeat(CU, Q, 0)
        Sa = np.repeat(Sa, Q, 0); SOa = np.repeat(SOa, Q, 0)
    fin, EE, NT = H._dyn(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(Sa),
                         np.ascontiguousarray(SOa), np.ascontiguousarray(A, dtype=np.float64), np.ascontiguousarray(Wd, dtype=np.float64),
                         float(cost), H.PP['tax'], H.DED, int(H.PP['harvest']), H.PP['hthr'], 21, 0.05, 0.25)
    return fin, EE, NT


def summary(fin, EE):
    T = EE.shape[1]; c = H.cagr(fin, T)
    import ce
    m = ce.mdd(EE)
    return dict(cagr=float(np.median(c)), p10=float(np.percentile(c, 10)), mdd=float(np.median(m)),
                dd80=float(np.mean(m <= -0.8)), n=int(len(c)))
