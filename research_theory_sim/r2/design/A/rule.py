"""Risk-Meter Leverage Clock rule (lane TS2 round 2, designer A).
Holds a Kelly-style base level p0 / sigma_long^2 + 0.5 (sigma_long = long-run vol estimate shrunk to a 17 % prior).
Leaves the market (level 0) when a fast variance meter runs above the slow 'risk meter' of leveraged traders by the
factor th_c^2 while the price is below its short trend: in the theory this is the forced-deleveraging cascade, whose
drift is negative while the meter is still rising. Re-enters at the base level as soon as the fast meter falls back
below the slow meter (the meter has peaked, forced selling is over). Pure numpy, causal, scale-invariant in close.
"""
import math
import numpy as np

INPUTS = ('close', 'rf')
PARAMS = {'p0': 0.02, 'th_c': 1.25, 'hl_f': 5.0, 'hl_m': 40.0, 'hl_tr': 20.0, 'th_r': 1.0}

_PRIOR_VOL = 0.17      # annual vol prior (published long-run anchor), not tuned
_PRIOR_YEARS = 5.0     # weight of the vol prior in years of data, not tuned
_DAYS = 252.0


def target_levels(close, rf, y10=None, params=PARAMS):
    p = dict(PARAMS)
    if params is not None:
        p.update(params)
    c = np.array(close, dtype=np.float64, copy=True)
    if c.ndim == 1:
        c = c[None, :]
    P, T = c.shape
    ok = np.isfinite(c) & (c > 0)
    lc = np.where(ok, np.log(np.where(ok, c, 1.0)), np.nan)
    # log return between consecutive valid closes; a day is 'live' only if it has a valid, nonzero return
    lr = np.zeros((P, T))
    last = np.full(P, np.nan)
    live = np.zeros((P, T), dtype=bool)
    for t in range(T):
        x = lc[:, t]
        good = np.isfinite(x)
        d = np.where(good & np.isfinite(last), x - np.where(np.isfinite(last), last, 0.0), 0.0)
        d = np.where(np.isfinite(d), d, 0.0)
        lr[:, t] = d
        live[:, t] = good & np.isfinite(last) & (d != 0.0)
        last = np.where(good, x, last)

    af = 1.0 - math.exp(math.log(0.5) / float(p['hl_f']))
    am = 1.0 - math.exp(math.log(0.5) / float(p['hl_m']))
    at = 1.0 - math.exp(math.log(0.5) / float(p['hl_tr']))
    thc2 = float(p['th_c']) ** 2
    thr2 = float(p['th_r']) ** 2
    p0 = float(p['p0'])
    v0 = _PRIOR_VOL ** 2 / _DAYS
    k = _PRIOR_YEARS * _DAYS

    vf = np.full(P, v0)            # fast variance meter
    vm = np.full(P, v0)            # slow 'risk meter'
    sq = np.zeros(P)               # sum of squared live returns
    n = np.zeros(P)                # number of live days
    lp = np.zeros(P)               # cumulative log price (scale-free)
    ema = np.zeros(P)              # short trend of the log price
    started = np.zeros(P, dtype=bool)
    out = np.zeros(P, dtype=bool)  # True = in the cascade (out of the market)
    B = np.full((P, T), np.nan)
    for t in range(T):
        x = lr[:, t]
        lv = live[:, t]
        lp = lp + x
        started = started | lv
        x2 = x * x
        vf = np.where(lv, (1 - af) * vf + af * x2, vf)
        vm = np.where(lv, (1 - am) * vm + am * x2, vm)
        sq = sq + np.where(lv, x2, 0.0)
        n = n + lv
        ema = np.where(started, (1 - at) * ema + at * lp, lp)
        vL = (sq + k * v0) / (n + k)
        casc = (vf > thc2 * vm) & (lp < ema)
        peaked = vf < thr2 * vm
        out = np.where(out, ~peaked, casc)
        base = np.clip(p0 / (vL * _DAYS) + 0.5, 0.0, 3.0)
        lev = np.where(out, 0.0, base)
        B[:, t] = np.where(started, lev, np.nan)
    return B
