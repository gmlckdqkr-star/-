"""Shared causal building blocks for XV1 candidates. Every function returns, at row t, a value that uses rows <= t only.
Inputs are 1-D float arrays on the view rows. NaN in an input gives NaN / False at the rows that depend on it."""
import numpy as np

FEE = 0.0095            # yearly fee of a leveraged fund model
SPREAD = 0.0075         # yearly financing spread per unit of borrowed exposure (3x: 0.0095 + 2 * 0.0075 = 0.0245, as the engine's 3x Nasdaq model)


def lev(r1, rf, L):
    """modelled daily-reset fund on the 1x daily return r1. L = 3, 2: L * r1 - (L - 1) * rf - (FEE + SPREAD * (L - 1)) / 252.
    L = -1 (inverse): -r1 + rf - FEE / 252.  L = 1 (plain index fund): r1 - 0.002 / 252."""
    if L == 1: return r1 - 0.002 / 252
    if L < 0: return L * r1 + rf - FEE / 252
    return L * r1 - (L - 1) * rf - (FEE + SPREAD * (L - 1)) / 252


def spliced(actual, model):
    """the actual fund return where it exists, the modelled one before (NaN where neither exists)"""
    return np.where(np.isnan(actual), model, actual)


def level(ret):
    """price level from daily returns; rows before the first valid return are NaN"""
    ok = ~np.isnan(ret); started = np.cumsum(ok) > 0
    out = np.cumprod(1 + np.where(ok, ret, 0.0)); out[~started] = np.nan
    return out


def sma(x, n):
    """mean of the last n rows (NaN until n valid rows in the window)"""
    out = np.full(len(x), np.nan); bad = np.isnan(x); c = np.cumsum(np.r_[0.0, np.where(bad, 0.0, x)]); nb = np.cumsum(np.r_[0, bad.astype(int)])
    if len(x) >= n:
        m = (c[n:] - c[:-n]) / n; m[(nb[n:] - nb[:-n]) > 0] = np.nan; out[n - 1:] = m
    return out


def roll_max(x, n):
    """highest value of the last n rows including row t (NaN rows ignored; NaN if the window has no value)"""
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        w = x[max(0, t - n + 1):t + 1]; w = w[~np.isnan(w)]
        if len(w): out[t] = w.max()
    return out


def roll_min(x, n): return -roll_max(-x, n)


def vol(ret, n):
    """annualised standard deviation of daily log returns over the last n rows"""
    lr = np.log1p(ret); out = np.full(len(ret), np.nan); bad = np.isnan(lr); z = np.where(bad, 0.0, lr)
    c1 = np.cumsum(np.r_[0.0, z]); c2 = np.cumsum(np.r_[0.0, z * z]); nb = np.cumsum(np.r_[0, bad.astype(int)])
    if len(ret) >= n:
        m = (c1[n:] - c1[:-n]) / n; v = np.maximum((c2[n:] - c2[:-n]) / n - m * m, 0.0) * 252
        s = np.sqrt(v); s[(nb[n:] - nb[:-n]) > 0] = np.nan; out[n - 1:] = s
    return out


def lag(x, n):
    """x[t - n] (NaN for the first n rows)"""
    out = np.full(len(x), np.nan)
    if n < len(x): out[n:] = x[:len(x) - n]
    return out


def hyst(on_cond, off_cond, start=False):
    """state flag: switches on at a row where on_cond holds, off at a row where off_cond holds, otherwise unchanged"""
    out = np.zeros(len(on_cond), dtype=bool); st = bool(start)
    for t in range(len(on_cond)):
        if st and off_cond[t]: st = False
        elif (not st) and on_cond[t]: st = True
        out[t] = st
    return out


def trend_flag(lvl, n=200, band=0.02):
    """on when lvl > (1 + band) * SMA_n, off when lvl < (1 - band) * SMA_n; off while the average does not exist"""
    s = sma(lvl, n); ok = ~np.isnan(s) & ~np.isnan(lvl)
    return hyst(ok & (lvl > s * (1 + band)), (~ok) | (lvl < s * (1 - band)))


def consec(cond):
    """number of consecutive rows ending at t on which cond holds"""
    out = np.zeros(len(cond), dtype=np.int64); k = 0
    for t in range(len(cond)):
        k = k + 1 if cond[t] else 0; out[t] = k
    return out


def debounce(x, n=3):
    """a discrete state that follows x only after x has shown the same new value on n consecutive rows"""
    out = np.empty(len(x), dtype=np.asarray(x).dtype); cur = x[0]; run = 0; prev = x[0]
    for t in range(len(x)):
        run = run + 1 if (t > 0 and x[t] == prev) else 1; prev = x[t]
        if x[t] != cur and run >= n: cur = x[t]
        out[t] = cur
    return out


def since(event):
    """rows since the last row on which event was True (a large number before the first event)"""
    out = np.empty(len(event), dtype=np.int64); k = 10 ** 9
    for t in range(len(event)):
        k = 0 if event[t] else min(k + 1, 10 ** 9); out[t] = k
    return out


# ---------------------------------------------------------------------------------------------- shared series
# nine sector slots for breadth: the sector SPDR once it has 200 rows of history, the Ken French industry before
SECTORS = (('XLK', 'BusEq'), ('XLE', 'Enrgy'), ('XLF', 'Money'), ('XLV', 'Hlth'), ('XLU', 'Utils'), ('XLP', 'NoDur'),
           ('XLI', 'Manuf'), ('XLY', 'Shops'), ('XLB', 'Telcm'))
SECTOR_NAMES = tuple('ret:' + a for a, _ in SECTORS) + tuple('kf:' + b for _, b in SECTORS)


def sector_returns(v):
    """(T, 9) daily returns of the nine sector slots"""
    out = np.empty((v.T, len(SECTORS)))
    for j, (a, b) in enumerate(SECTORS):
        e = v.x['ret:' + a]; k = v.x['kf:' + b]; have = np.cumsum(~np.isnan(e)) >= 200
        out[:, j] = np.where(have & ~np.isnan(e), e, k)
    return out


def breadth(v, n=200):
    """share of the nine sector series above their own n-day average (NaN until the averages exist)"""
    R = sector_returns(v); up = np.zeros(v.T); cnt = np.zeros(v.T)
    for j in range(R.shape[1]):
        l = level(R[:, j]); s = sma(l, n); ok = ~np.isnan(s) & ~np.isnan(l)
        up += ok & (l > s); cnt += ok
    return np.where(cnt == R.shape[1], up / np.maximum(cnt, 1), np.nan)


def ndx_level(v): return np.asarray(v.c.lvl[0], dtype=np.float64)


def semis_level(v):
    """1x semiconductor level: Ken French Chips until SOXX exists, SOXX afterwards"""
    return level(v.x['semis'])


def fund(v, key, base_r, L):
    """daily return of a leveraged or inverse fund: the fund itself ('ret:KEY' in v.x) where it exists, before that the model
    on the 1x return base_r"""
    return spliced(v.x['ret:' + key], lev(base_r, v.c.rf[0], L))
