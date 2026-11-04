"""Candidate rule family for selection (same code path as the final rule.py, but with params as arguments).
L = clip((c + a*log(v_hs/v_hss) + b*log(v_hm/v_hs)) / (252*v_hf), 0, Lmax)
v_h = debiased EWMA (half-life h days) of squared daily log returns over valid days (finite, > 0, non-zero change)."""
import numpy as np


def _dewma_multi(g2, ok, hls):
    P, T = g2.shape
    al = [1 - 0.5 ** (1.0 / h) for h in hls]
    num = [np.zeros(P) for _ in hls]; den = [np.zeros(P) for _ in hls]
    out = [np.full((P, T), np.nan) for _ in hls]
    for t in range(T):
        o = ok[:, t]; x = g2[:, t]
        for i, a in enumerate(al):
            num[i] = np.where(o, (1 - a) * num[i] + a * x, num[i])
            den[i] = np.where(o, (1 - a) * den[i] + a, den[i])
            out[i][:, t] = np.where(den[i] > 0, num[i] / np.where(den[i] > 0, den[i], 1.0), np.nan)
    return out


def prep(close):
    c = np.array(close, dtype=np.float64, copy=True)
    prev = np.full_like(c, np.nan); prev[:, 1:] = c[:, :-1]
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    g = np.zeros_like(c)
    g[ok] = np.log(c[ok] / prev[ok])
    ok &= (g != 0.0)
    g[~ok] = 0.0
    nobs = np.cumsum(ok, axis=1)
    return g, ok, nobs


def levels(close, c=0.02, a=0.2, b=0.04, hf=20, hs=250, hss=1000, hm=60, Lmax=3.0, nmin=250, cache=None):
    if cache is None: cache = {}
    if 'prep' not in cache: cache['prep'] = prep(close)
    g, ok, nobs = cache['prep']
    need = [h for h in sorted({hf, hs, hss, hm}) if h not in cache]
    if need:
        for h, v in zip(need, _dewma_multi(g * g, ok, need)): cache[h] = v
    vf, vs, vss, vm = cache[hf], cache[hs], cache[hss], cache[hm]
    with np.errstate(divide='ignore', invalid='ignore'):
        mhat = c + a * np.log(vs / vss) + b * np.log(vm / vs)
        L = mhat / (252.0 * vf)
    L = np.clip(L, 0.0, Lmax)
    L[~np.isfinite(L)] = np.nan
    L[nobs < nmin] = np.nan
    return L
