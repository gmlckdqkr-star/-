"""Two-clock Kelly rule (lane TS2 round 2, designer B; theory: two-clock yardstick learning).
Risk is learned fast: the level is a fractional Kelly bet k * e / s^2 on a 20-day estimate s of current volatility.
The premium is learned slowly and over-extrapolated by the market: e starts from the anchored premium mu0 = 3% and is
lowered after a strong trailing year of excess returns (and raised after a weak one), b_hope * (hope - mu0).
Uses only close (log changes, so scale-invariant) and rf up to t; invalid or flat days do not update the estimates.
Output: target level in [0, 3] (NaN = cash until 60 valid returns exist).
"""
import numpy as np
import math

INPUTS = ('close', 'rf')
PARAMS = {'k': 0.6, 'mu0': 0.03, 'h_vol': 20.0, 'b_hope': 0.1, 'h_hope_years': 1.0}


def target_levels(close, rf, y10=None, params=PARAMS):
    c = np.array(close, dtype=np.float64, copy=True)
    f = np.array(rf, dtype=np.float64, copy=True)
    if c.ndim == 1:
        c = c[None, :]
        f = f[None, :]
    P, T = c.shape
    k, mu0 = float(params['k']), float(params['mu0'])
    lam_v = 1.0 - 0.5 ** (1.0 / float(params['h_vol']))
    lam_h = 1.0 - 0.5 ** (1.0 / (252.0 * float(params['h_hope_years'])))
    b = float(params['b_hope'])
    sq = 1.25 * math.sqrt(252.0)
    s0 = 0.17
    good = np.isfinite(c) & (c > 0)
    lc = np.where(good, np.log(np.where(good, c, 1.0)), np.nan)
    s = np.full(P, s0)                       # annualised vol estimate (fast clock)
    m = np.full(P, mu0 - s0 * s0 / 2)        # experienced annualised log excess return (slow clock, the market's hope)
    last = np.full(P, np.nan)                # last valid log close
    rf_last = np.zeros(P)
    nvalid = np.zeros(P)
    out = np.full((P, T), np.nan)
    for t in range(T):
        rft = f[:, t]
        rf_last = np.where(np.isfinite(rft), rft, rf_last)
        lt = lc[:, t]
        x = lt - last
        ok = np.isfinite(x) & (x != 0.0)
        xs = np.where(ok, x, 0.0)
        s = np.where(ok, s + lam_v * (sq * np.abs(xs) - s), s)
        m = np.where(ok, m + lam_h * (252.0 * (xs - rf_last) - m), m)
        nvalid = nvalid + ok
        last = np.where(np.isfinite(lt), lt, last)
        e = mu0 - b * (m + s * s / 2 - mu0)
        L = np.clip(k * e / np.maximum(s * s, 1e-6), 0.0, 3.0)
        out[:, t] = np.where(nvalid >= 60, L, np.nan)
    return out
