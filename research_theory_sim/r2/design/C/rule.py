"""FASS rule ("Fast Aftershocks, Slow Scars"), lane TS2 r2, designer C.
Growth (Kelly-type) exposure = expected excess return / variance, with two clocks taken from the theory:
the reward estimate is slow: a prior premium c plus a "scar" term that rises when the past year's variance is high relative
to the long run (perceived-crash scar and insurer-capital overshoot still unwinding) and when the last quarter is turbulent
relative to the year; the risk estimate is fast: a short half-life variance, so exposure falls within days of a crash cluster.
Exposure is in index units, clipped to [0, 3]; cash (NaN) until 250 valid daily returns exist. Uses close only (rf unused).
"""
import math
import numpy as np

INPUTS = ('close', 'rf')
PARAMS = {'c': 0.02, 'a': 0.2, 'b': 0.08, 'hf': 40, 'hs': 350}
# fixed structure (not tuned): very slow half-life = 4*hs, mid half-life = hs/4, cap 3, 250 valid returns before trading.


def _dewma(g2, ok, hls):
    """Debiased EWMAs (one per half-life) of g2 along axis 1; days with ok False do not update."""
    P, T = g2.shape
    al = [1.0 - math.pow(0.5, 1.0 / h) for h in hls]
    num = [np.zeros(P) for _ in hls]
    den = [np.zeros(P) for _ in hls]
    out = [np.full((P, T), np.nan) for _ in hls]
    for t in range(T):
        o = ok[:, t]
        x = g2[:, t]
        for i, a in enumerate(al):
            num[i] = np.where(o, (1.0 - a) * num[i] + a * x, num[i])
            den[i] = np.where(o, (1.0 - a) * den[i] + a, den[i])
            pos = den[i] > 0
            out[i][:, t] = np.where(pos, num[i] / np.where(pos, den[i], 1.0), np.nan)
    return out


def target_levels(close, rf, y10=None, params=PARAMS):
    c = np.array(close, dtype=np.float64, copy=True)
    if c.ndim == 1:
        c = c[None, :]
    P, T = c.shape
    prev = np.full_like(c, np.nan)
    prev[:, 1:] = c[:, :-1]
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    g = np.zeros_like(c)
    g[ok] = np.log(c[ok] / prev[ok])
    ok &= (g != 0.0)                       # flat stretches (no trading) do not update the filters
    g[~ok] = 0.0
    nobs = np.cumsum(ok, axis=1)
    hf = float(params['hf']); hs = float(params['hs'])
    vf, vm, vs, vss = _dewma(g * g, ok, [hf, hs / 4.0, hs, 4.0 * hs])
    with np.errstate(divide='ignore', invalid='ignore'):
        mhat = params['c'] + params['a'] * np.log(vs / vss) + params['b'] * np.log(vm / vs)
        L = mhat / (252.0 * vf)
    L = np.clip(L, 0.0, 3.0)
    L[~np.isfinite(L)] = np.nan
    L[nobs < 250] = np.nan
    return L
