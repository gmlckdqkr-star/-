"""Causal feature helpers for rule exploration (data <= t only). Scale-invariant: they use log returns only."""
import numpy as np

V0 = 0.175 ** 2 / 252          # prior daily variance (anchor), used only to initialise filters


def logret(close):
    c = np.asarray(close, dtype=np.float64)
    prev = np.empty_like(c); prev[:, 0] = np.nan; prev[:, 1:] = c[:, :-1]
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    g = np.zeros_like(c)
    g[ok] = np.log(c[ok] / prev[ok])
    return g, ok


def ewma(x, hl, ok=None, init=None):
    """EWMA along axis 1 with half-life hl days; columns where ok is False do not update."""
    P, T = x.shape
    a = 1 - 0.5 ** (1.0 / hl)
    out = np.empty((P, T))
    m = np.full(P, init if init is not None else 0.0)
    for t in range(T):
        if ok is None:
            m = m + a * (x[:, t] - m)
        else:
            m = np.where(ok[:, t], m + a * (x[:, t] - m), m)
        out[:, t] = m
    return out
