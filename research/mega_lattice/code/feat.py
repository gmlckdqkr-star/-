"""Mega-lattice features (PRECOMMIT_ML.md sec 2). Pure numpy/pandas so the same code runs inside the lab plugin.
feats(p, month) -> DataFrame (40 columns) ; value at row t uses closes <= t only."""
import numpy as np
import pandas as pd

NAMES = ['z5', 'z10', 'z21', 'z63', 'z126', 'z252', 'd10', 'd20', 'd50', 'd100', 'd200', 'vr10_63', 'vr21_252',
         'vr63_252', 'vol21', 'volvol', 'dd252', 'ddall', 'reb63', 'since_hi', 'since_crash', 'trend_age', 'up21',
         'up63', 'rsi14', 'skew63', 'ac63', 'maxl21', 'maxg21', 'er21', 'er63', 'vr5', 'd200chg', 'z252chg',
         'slope200', 'ma50_200', 'mup12', 'season']
# 38 listed above + 2 below = 40
NAMES += ['vol63', 'ret_1']


def _since_true(ev):
    out = np.empty(len(ev)); last = -10 ** 9
    for i in range(len(ev)):
        if ev[i]:
            last = i
        out[i] = min(i - last, 2000) if last > -10 ** 9 else 2000.0
    return out


def _since_high(lp, n=252):
    out = np.full(len(lp), np.nan)
    from collections import deque
    dq = deque()
    for i in range(len(lp)):
        while dq and lp[dq[-1]] <= lp[i]:
            dq.pop()
        dq.append(i)
        while dq[0] <= i - n:
            dq.popleft()
        if i >= n - 1:
            out[i] = i - dq[0]
    return out


def _trend_age(above):
    out = np.zeros(len(above)); run = 0; prev = None
    for i, a in enumerate(above):
        if a is None or (isinstance(a, float) and np.isnan(a)):
            out[i] = np.nan; prev = None; run = 0; continue
        run = run + 1 if a == prev else 1
        prev = a
        out[i] = run if a else -run
    return out


def feats(p, month):
    p = pd.Series(np.asarray(p, float), index=p.index)
    lp = np.log(p); r = lp.diff()
    s10 = r.rolling(10).std(); s21 = r.rolling(21).std(); s63 = r.rolling(63).std(); s252 = r.rolling(252).std()
    F = {}
    for n in (5, 10, 21, 63, 126, 252):
        F['z%d' % n] = (lp - lp.shift(n)) / (s63 * np.sqrt(n))
    sma = {n: p.rolling(n).mean() for n in (10, 20, 50, 100, 200)}
    for n in (10, 20, 50, 100, 200):
        F['d%d' % n] = (lp - np.log(sma[n])) / s63
    F['vr10_63'] = np.log(s10 / s63); F['vr21_252'] = np.log(s21 / s252); F['vr63_252'] = np.log(s63 / s252)
    F['vol21'] = s21 * np.sqrt(252)
    F['volvol'] = s21.rolling(252).std() / s21.rolling(252).mean()
    F['dd252'] = lp - np.log(p.rolling(252).max())
    F['ddall'] = lp - np.log(p.cummax())
    F['reb63'] = lp - np.log(p.rolling(63).min())
    F['since_hi'] = pd.Series(_since_high(lp.values), index=p.index)
    crash = (r < -2.5 * s63.shift(1)).values
    sc = _since_true(crash); sc[:64] = np.nan
    F['since_crash'] = pd.Series(sc, index=p.index)
    ab = (p > sma[200]).astype(float).where(sma[200].notna())
    F['trend_age'] = pd.Series(_trend_age([None if np.isnan(x) else bool(x) for x in ab.values]), index=p.index)
    F['up21'] = (r > 0).astype(float).rolling(21).mean(); F['up63'] = (r > 0).astype(float).rolling(63).mean()
    g = r.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); l_ = (-r.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    F['rsi14'] = 100 - 100 / (1 + g / l_)
    F['skew63'] = r.rolling(63).skew()
    F['ac63'] = r.rolling(63).corr(r.shift(1))
    F['maxl21'] = r.rolling(21).min() / s63; F['maxg21'] = r.rolling(21).max() / s63
    ar = r.abs()
    for n in (21, 63):
        F['er%d' % n] = (lp - lp.shift(n)).abs() / ar.rolling(n).sum()
    r5 = lp - lp.shift(5)
    F['vr5'] = r5.rolling(252).var() / (5 * r.rolling(252).var())
    F['d200chg'] = F['d200'] - F['d200'].shift(21)
    F['z252chg'] = F['z252'] - F['z252'].shift(63)
    F['slope200'] = (np.log(sma[200]) - np.log(sma[200].shift(21))) / s63
    F['ma50_200'] = (np.log(sma[50]) - np.log(sma[200])) / s63
    m = 0
    for k in range(12):
        m = m + ((lp.shift(21 * k) - lp.shift(21 * (k + 1))) > 0).astype(float).where(lp.shift(21 * (k + 1)).notna())
    F['mup12'] = m / 12
    mo = np.asarray(month, float)
    F['season'] = pd.Series(np.select([np.isin(mo, [11, 12, 1]), np.isin(mo, [2, 3, 4]), np.isin(mo, [5, 6, 7])],
                                      [0.0, 1.0, 2.0], 3.0), index=p.index)
    F['vol63'] = s63 * np.sqrt(252)
    F['ret_1'] = r / s63
    D = pd.DataFrame(F, index=p.index)[NAMES]
    return D.replace([np.inf, -np.inf], np.nan)


def binize(D, edges):
    """edges: dict name -> sorted array of interior cut points (season: None = use value). Returns int8 array, -1 = NaN."""
    B = np.full(D.shape, -1, np.int8)
    for j, nm in enumerate(NAMES):
        v = D[nm].values
        ok = ~np.isnan(v)
        if edges[nm] is None:
            B[ok, j] = v[ok].astype(np.int8)
        else:
            B[ok, j] = np.searchsorted(edges[nm], v[ok], side='right').astype(np.int8)
    return B
