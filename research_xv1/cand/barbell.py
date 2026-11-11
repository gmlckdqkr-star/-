"""Owner's barbell (2026-11-11): v1 next to a small aggressive sleeve in the 3x semiconductor fund, with rules that move
sleeve profits into v1 (skim), and optionally refill the sleeve from v1 after losses.

Sleeve instrument: SOXL where it exists, before that the modelled 3x of the semiconductor index (SOXX, before SOXX the
Ken French Chips industry) with the same yearly drag as the 3x Nasdaq fund model. The sleeve has priority (mode 1): it takes
its share of the account, v1 runs unchanged on the rest."""
import numpy as np
import xv1

NAMES = ('ret:SOXL', 'semis')
YEAR = 252


def _sleeve(v):
    a = v.x['ret:SOXL']; s = v.x['semis']; rf = v.c.rf[0]
    return np.where(np.isnan(a), 3 * s - 2 * rf - 0.0245 / 252, a)


def _trend(v, n=200, band=0.02):
    """semiconductor index above its own n-day average, with a +-band switch; built from the 1x series only"""
    s = np.nan_to_num(v.x['semis']); lvl = np.cumprod(1 + s)
    c = np.cumsum(np.r_[0.0, lvl]); sma = np.full(v.T, np.nan); sma[n - 1:] = (c[n:] - c[:-n]) / n
    on = np.zeros(v.T, dtype=bool); st = False
    for t in range(v.T):
        if np.isnan(sma[t]) or np.isnan(v.x['semis'][t]): st = False
        elif st and lvl[t] < sma[t] * (1 - band): st = False
        elif (not st) and lvl[t] > sma[t] * (1 + band): st = True
        on[t] = st
    return on


def sleeve(v, w=0.10, rule='skim', held='always', band=0.25):
    """w     target share of the account in the sleeve
    rule  'skim'   one way: when the sleeve is above w x (1 + band) it is cut back to w and the money goes to v1; never refilled
          'band'   two way: also refilled from v1 when it is below w x (1 - band)
          'yearly' two way: re-set to w every 252 rows (counted from the first row on which the sleeve exists), no bands
    held  'always' the sleeve is always held;  'trend' only while the semiconductor index is above its 200-day average (+-2%)"""
    o = xv1.ref(v); g = _sleeve(v); ok = ~np.isnan(g)
    on = ok if held == 'always' else (ok & _trend(v))
    W = np.where(on, w, 0.0); RB = np.zeros(v.T); up = dn = None
    if rule == 'skim': up = np.array([band])
    elif rule == 'band': up = np.array([band]); dn = np.array([band])
    elif rule == 'yearly':
        age = np.cumsum(ok) - 1; RB[ok & (age > 0) & (age % YEAR == 0)] = 1.0
    else: raise ValueError(rule)
    o.update(G=g[:, None], Wt=W[:, None], mode=1, inc=0, RB=RB[:, None])
    if up is not None: o['up'] = up
    if dn is not None: o['dn'] = dn
    return o


def always(v, w=0.10, rule='skim', band=0.25):
    """the sleeve is always held (one family)"""
    return sleeve(v, w, rule, 'always', band)


def trend(v, w=0.10, rule='skim', band=0.25):
    """the sleeve is held only while the semiconductor index is above its 200-day average (another family)"""
    return sleeve(v, w, rule, 'trend', band)
