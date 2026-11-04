"""GH1 A: LPPLS bubble-confidence exit (Sornette LPPLS, idea from Boulder-Investment-Technologies/lppls, MIT;
own numpy re-implementation, no code copied). Row t uses rows <= t only. Evaluated every `every` rows (by position)."""
import numpy as np
import pandas as pd

_CACHE = {}


def _conf(lp, pos, wins, dgrid, mgrid, wgrid):
    key = (pos, float(lp[pos]))
    if key in _CACHE:
        return _CACHE[key]
    n_ok = 0; n_w = 0
    for L in wins:
        if pos + 1 < L:
            continue
        n_w += 1
        y = lp[pos - L + 1: pos + 1]
        t = np.arange(L, dtype=float)
        D, M, W = np.meshgrid(np.asarray(dgrid), np.asarray(mgrid), np.asarray(wgrid), indexing='ij')
        D = D.ravel(); M = M.ravel(); W = W.ravel()
        tau = (L - 1 + D[:, None]) - t[None, :]
        lt = np.log(tau)
        f = tau ** M[:, None]
        X = np.stack([np.ones_like(f), f, f * np.cos(W[:, None] * lt), f * np.sin(W[:, None] * lt)], axis=2)
        XtX = np.einsum('gli,glj->gij', X, X) + 1e-10 * np.eye(4)[None]
        Xty = np.einsum('gli,l->gi', X, y)
        beta_all = np.linalg.solve(XtX, Xty[:, :, None])[:, :, 0]
        sse_all = ((np.einsum('gli,gi->gl', X, beta_all) - y[None, :]) ** 2).sum(axis=1)
        g = int(np.argmin(sse_all))
        d, m, w, beta = float(D[g]), float(M[g]), float(W[g]), beta_all[g]
        B = beta[1]; C = float(np.hypot(beta[2], beta[3]))
        damp = (m * abs(B)) / (w * C) if C > 0 else np.inf
        osc = (w / (2 * np.pi)) * np.log((L - 1 + d) / d)
        if B < 0 and damp >= 0.8 and osc >= 2.5:
            n_ok += 1
    c = (n_ok / n_w) if n_w else 0.0
    _CACHE[key] = c
    return c


def weights(F, sleeves, params):
    px = F[params.get('col', 'QQQ')].values.astype(float)
    lp = np.log(px)
    every = int(params.get('every', 21)); thr = float(params.get('thr', 2 / 3)); hold = int(params.get('hold', 0))
    wins = [int(x) for x in params.get('wins', [126, 252, 504])]
    dgrid = [float(x) for x in params.get('d', [10, 30, 60])]
    mgrid = [float(x) for x in params.get('m', [0.2, 0.5, 0.8])]
    wgrid = [float(x) for x in params.get('w', [7, 10, 13])]
    n = len(px); out = np.zeros(n); bub = False; cash_until = -1
    base = None
    if 'base' in params:
        base = F[params['base']].values.astype(float)
    for t in range(n):
        if not np.isfinite(lp[t]):
            out[t] = 0.0; continue
        if t % every == 0:
            c = _conf(lp, t, wins, dgrid, mgrid, wgrid)
            bub = c >= thr - 1e-12
            if bub and hold > 0:
                cash_until = t + hold
        risk_off = bub or (t < cash_until)
        on = 1.0 if base is None else (1.0 if base[t] > 0.5 else 0.0)
        out[t] = 0.0 if risk_off else on
    return pd.DataFrame({sleeves[0]: out}, index=F.index)
