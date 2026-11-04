"""Dealer Ledger rule (lane TS1, designer L2).
Estimates the hidden intermediary capital ledger as a decayed sum (half-life 1.5 y) of past excess log returns.
A depleted ledger means a high price of risk, so the expected excess drift is a0 - a1*ledger, plus a funding-cost
term a3*(short rate - its slow 5-year norm): rate shocks depress prices now and are earned back later.
The level is a Kelly-style ratio of that drift to a running variance (EWMA of squared log returns, half-life 140 days),
clipped to [0, 3]; zero drift or worse means cash. Causal: column t uses only columns <= t. Scale-invariant in close.
"""
import math
import numpy as np

INPUTS = ('close', 'rf')
PARAMS = {'hv_days': 140.0, 'ledger_hl_years': 1.5, 'a0': 0.03, 'a1': 0.2, 'a3': 1.0}

_NORM_HL_YEARS = 5.0     # slow norm of the short rate: fixed by THEORY.md (5-year payout norm), not tuned
_VAR_FLOOR = 0.0004      # numerical guard on the annualised variance estimate (= 2% vol)
_START = 20              # columns before this are NaN (cash); the first 300 columns are warm-up anyway


def target_levels(close, rf, y10=None, params=PARAMS):
    close = np.asarray(close, dtype=np.float64)
    rf = np.asarray(rf, dtype=np.float64)
    one = close.ndim == 1
    if one:
        close = close[None, :]; rf = rf[None, :]
    P, T = close.shape
    hv = float(params['hv_days']); hl = float(params['ledger_hl_years']) * 252.0
    a0 = float(params['a0']); a1 = float(params['a1']); a3 = float(params['a3'])
    lam_v = math.pow(0.5, 1.0 / hv)
    lam_l = math.pow(0.5, 1.0 / hl)
    lam_r = math.pow(0.5, 1.0 / (_NORM_HL_YEARS * 252.0))

    with np.errstate(divide='ignore', invalid='ignore'):
        lc = np.log(np.where(close > 0, close, np.nan))
    lr = np.full((P, T), np.nan)
    lr[:, 1:] = lc[:, 1:] - lc[:, :-1]

    out = np.full((P, T), np.nan)
    vm = np.zeros(P); vw = np.zeros(P)          # EWMA of squared log returns (bias-corrected)
    led = np.zeros(P)                           # ledger estimate: decayed sum of excess log returns
    rm = np.zeros(P); rw = np.zeros(P)          # EWMA of the annual short rate (bias-corrected)
    rf_last = np.zeros(P)
    for t in range(T):
        rft = rf[:, t]
        okr = np.isfinite(rft)
        rf_last = np.where(okr, rft, rf_last)   # forward-fill missing rates
        x = lr[:, t]
        ok = np.isfinite(x)
        xs = np.where(ok, x, 0.0)
        vm = np.where(ok, lam_v * vm + (1 - lam_v) * xs * xs, vm)
        vw = np.where(ok, lam_v * vw + (1 - lam_v), vw)
        led = lam_l * led + np.where(ok, xs - rf_last, 0.0)
        rfa = rf_last * 252.0
        rm = np.where(okr, lam_r * rm + (1 - lam_r) * rfa, rm)
        rw = np.where(okr, lam_r * rw + (1 - lam_r), rw)
        if t < _START:
            continue
        var = np.where(vw > 0, vm / np.where(vw > 0, vw, 1.0), np.nan) * 252.0
        var = np.maximum(var, _VAR_FLOOR)
        gap = np.where(rw > 0, rfa - rm / np.where(rw > 0, rw, 1.0), 0.0)
        mu = a0 - a1 * led + a3 * gap
        L = np.clip(mu / var, 0.0, 3.0)
        out[:, t] = np.where(np.isfinite(var), L, np.nan)
    return out[0] if one else out
