"""TS1 L1 (MRLC) frozen rule, code copied verbatim from design/L1/rule.py, wrapped for the lab plugin contract.
Weights: TQQQ = level/3, rest CASH. Inputs: QQQ (= NDX level in lab), _IRX (percent) -> rf = _IRX/100/252."""

import numpy as np
import math

INPUTS = ('close', 'rf')
PARAMS = {'m0': 0.08, 'A': 1.25, 'ns': 42, 'B': 0.5, 'nl': 252, 'sv': 120}
_KF = 0.5            # half Kelly (fixed constant, never tuned)
_VFLOOR = 0.03 ** 2  # annual variance floor


def _ffill(x):
    x = np.array(x, dtype=np.float64, copy=True)
    P, T = x.shape
    last = np.full(P, np.nan)
    for t in range(T):
        col = x[:, t]
        ok = np.isfinite(col)
        last = np.where(ok, col, last)
        x[:, t] = last
    return x


def target_levels(close, rf, y10=None, params=PARAMS):
    close = np.asarray(close, dtype=np.float64)
    rf = np.asarray(rf, dtype=np.float64)
    one_d = close.ndim == 1
    if one_d:
        close = close[None, :]
        rf = rf[None, :]
    P, T = close.shape
    c = _ffill(np.where(close > 0, close, np.nan))
    valid = np.isfinite(c)
    lp = np.log(np.where(valid, c, 1.0))
    rfa = _ffill(rf)
    rfa = np.where(np.isfinite(rfa), rfa, 0.0) * 252.0

    a_s = 2.0 / (float(params['ns']) + 1.0)
    a_l = 2.0 / (float(params['nl']) + 1.0)
    a_v = 2.0 / (float(params['sv']) + 1.0)
    m0, A, B = float(params['m0']), float(params['A']), float(params['B'])

    out = np.full((P, T), np.nan)
    es = np.full(P, np.nan)          # EMA of log price, short
    el = np.full(P, np.nan)          # EMA of log price, long
    vraw = np.zeros(P)               # EWMA of squared log returns (bias-corrected below)
    wsum = np.zeros(P)
    prev = np.full(P, np.nan)
    for t in range(T):
        ok = valid[:, t]
        x = lp[:, t]
        r = np.where(ok & np.isfinite(prev), x - prev, np.nan)
        hasr = np.isfinite(r)
        vraw = np.where(hasr, vraw + a_v * (r * r - vraw), vraw)
        wsum = np.where(hasr, wsum + a_v * (1.0 - wsum), wsum)
        es = np.where(ok, np.where(np.isfinite(es), es + a_s * (x - es), x), es)
        el = np.where(ok, np.where(np.isfinite(el), el + a_l * (x - el), x), el)
        prev = np.where(ok, x, prev)
        var = np.where(wsum > 0, vraw / np.where(wsum > 0, wsum, 1.0), np.nan) * 252.0
        var = np.maximum(var, _VFLOOR)
        mu = m0 + A * (x - es) - B * (x - el) - rfa[:, t]
        L = _KF * mu / var
        L = np.clip(L, 0.0, 3.0)
        out[:, t] = np.where(ok & (wsum > 0), L, np.nan)
    return out[0] if one_d else out


def weights(F, sleeves, params):
    import pandas as pd
    close = F['QQQ'].values.astype(float)[None, :]
    rf = (F['_IRX'].values.astype(float) / 100.0 / 252.0)[None, :]
    L = target_levels(close, rf)[0]
    L = np.where(np.isfinite(L), L, 0.0)
    return pd.DataFrame({sleeves[0]: L / 3.0}, index=F.index)
