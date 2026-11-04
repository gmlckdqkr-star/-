"""SGNC-K: Kelly sizing on the narrative-contagion trend (lane TS1, blind designer L3).
A story change spreads slowly (contagion gated by attention), so the excess return of the last ~6 months, in units of
its own volatility (z), predicts the drift of the coming months; with no fresh story the premium is small.
Forecast f = a + beta*z (annual excess return); target level = f / sigma^2 (fractional Kelly), clipped to [0, 3].
sigma^2 is an EWMA of squared daily log returns; NaN target (cash) until 20 valid returns exist.
Pure numpy, causal (column t uses data <= t only), scale-invariant in close (uses log returns only).
"""
import numpy as np
import math

INPUTS = ('close', 'rf')
PARAMS = {'a': 0.005, 'beta': 0.01, 'N': 126, 'Hv': 60}


def target_levels(close, rf, y10=None, params=PARAMS):
    a = float(params['a']); beta = float(params['beta']); N = int(params['N']); Hv = float(params['Hv'])
    c = np.asarray(close, dtype=np.float64)
    if c.ndim == 1:
        c = c[None, :]
    P, T = c.shape
    f = np.asarray(rf, dtype=np.float64)
    if f.ndim == 1:
        f = f[None, :]
    f = np.broadcast_to(f, (P, T))
    av = 1.0 - 0.5 ** (1.0 / Hv)
    out = np.full((P, T), np.nan)
    last = np.full(P, np.nan)          # last valid close
    rf_last = np.zeros(P)              # last valid rf
    S = np.zeros(P); W = np.zeros(P)   # bias-corrected EWMA of squared log returns
    cnt = np.zeros(P)                  # number of valid returns so far
    ring = np.zeros((P, N))            # last N excess log returns (0 for missing days)
    csum = np.zeros(P)                 # sum over the ring
    for t in range(T):
        ct = c[:, t]
        rt = f[:, t]
        rf_last = np.where(np.isfinite(rt), rt, rf_last)
        ok = np.isfinite(ct) & (ct > 0) & np.isfinite(last) & (last > 0)
        lr = np.zeros(P)
        lr[ok] = np.log(ct[ok] / last[ok])
        ex = np.where(ok, lr - rf_last, 0.0)
        j = t % N
        csum = csum - ring[:, j] + ex
        ring[:, j] = ex
        S = np.where(ok, (1.0 - av) * S + lr * lr, S)
        W = np.where(ok, (1.0 - av) * W + 1.0, W)
        cnt = cnt + ok
        last = np.where(np.isfinite(ct) & (ct > 0), ct, last)
        v = np.where(W > 0, S / np.maximum(W, 1e-300), 0.0)
        good = (cnt >= 20) & (v > 0)
        n_eff = np.minimum(cnt, N)
        z = csum / np.sqrt(np.maximum(v * n_eff, 1e-300))
        lev = (a + beta * z) / np.maximum(252.0 * v, 1e-300)
        out[:, t] = np.where(good, np.clip(lev, 0.0, 3.0), np.nan)
    return out
