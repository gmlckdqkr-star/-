"""GH2: LPPLS multi-window confidence, positive (bubble) and negative (anti-bubble) indicators, standard filters
(m 0.1-0.9, omega 6-13, damping >= 0.5, oscillations >= 2.5, tc - t2 <= 0.2 * window). Own numpy implementation.
Row t uses rows <= t only. Evaluated every `every` rows by position; state held until the next evaluation."""
import numpy as np
import pandas as pd

_CACHE = {}
WINS = (60, 120, 180, 240, 300, 360, 420, 480)
DG = (5.0, 20.0, 60.0)
MG = (0.2, 0.5, 0.8)
WG = (6.5, 9.5, 12.5)


def _fit(y, L):
    t = np.arange(L, dtype=float)
    D, M, W = np.meshgrid(np.asarray(DG), np.asarray(MG), np.asarray(WG), indexing='ij')
    D = D.ravel(); M = M.ravel(); W = W.ravel()
    keep = D <= 0.2 * L
    D, M, W = D[keep], M[keep], W[keep]
    tau = (L - 1 + D[:, None]) - t[None, :]
    lt = np.log(tau)
    f = tau ** M[:, None]
    X = np.stack([np.ones_like(f), f, f * np.cos(W[:, None] * lt), f * np.sin(W[:, None] * lt)], axis=2)
    XtX = np.einsum('gli,glj->gij', X, X) + 1e-10 * np.eye(4)[None]
    Xty = np.einsum('gli,l->gi', X, y)
    beta = np.linalg.solve(XtX, Xty[:, :, None])[:, :, 0]
    sse = ((np.einsum('gli,gi->gl', X, beta) - y[None, :]) ** 2).sum(axis=1)
    g = int(np.argmin(sse))
    d, m, w, b = float(D[g]), float(M[g]), float(W[g]), beta[g]
    B = b[1]; C = float(np.hypot(b[2], b[3]))
    damp = (m * abs(B)) / (w * C) if C > 0 else np.inf
    osc = (w / (2 * np.pi)) * np.log((L - 1 + d) / d)
    ok = damp >= 0.5 and osc >= 2.5
    return (1 if (ok and B < 0) else 0), (1 if (ok and B > 0) else 0)


def _conf(lp, pos):
    key = (pos, float(lp[pos]))
    if key in _CACHE:
        return _CACHE[key]
    npos = nneg = nw = 0
    for L in WINS:
        if pos + 1 < L:
            continue
        y = lp[pos - L + 1: pos + 1]
        if not np.all(np.isfinite(y)):
            continue
        nw += 1
        a, b = _fit(y, L)
        npos += a; nneg += b
    r = (npos / nw, nneg / nw) if nw else (0.0, 0.0)
    _CACHE[key] = r
    return r


def weights(F, sleeves, params):
    px = F[params.get('col', 'QQQ')].values.astype(float)
    lp = np.log(px)
    every = int(params.get('every', 21)); thr = float(params.get('thr', 0.25))
    nthr = float(params.get('nthr', 9.0)); hold = int(params.get('hold', 0)); boost = int(params.get('boost', 63))
    on_sleeve = params.get('lev', sleeves[0]); base_sleeve = params.get('base_sleeve', on_sleeve)
    gate = F[params['gate']].values.astype(float) if 'gate' in params else None
    n = len(px); W = {s: np.zeros(n) for s in sleeves}
    bub = False; cash_until = -1; boost_until = -1
    for t in range(n):
        if not np.isfinite(lp[t]):
            continue
        if t % every == 0:
            pc, nc = _conf(lp, t)
            bub = pc >= thr - 1e-12
            if bub and hold > 0:
                cash_until = t + hold
            if nc >= nthr - 1e-12:
                boost_until = t + boost
        if bub or t < cash_until:
            continue
        if gate is not None and not gate[t] > 0.5:
            continue
        s = on_sleeve if t < boost_until else base_sleeve
        W[s][t] = 1.0
    return pd.DataFrame(W, index=F.index)
