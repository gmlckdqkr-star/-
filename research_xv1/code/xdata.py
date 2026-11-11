"""Instrument and signal inputs for XV1 candidates, aligned to the context rows c.idx (T rows: warm-up + account days).

These arrays are FULL (they include sealed days) because the account is continuous. They are for use inside candidate code and the
engine only: never print, plot or save them. Anything shown to a person must go through xv1 (which masks sealed days)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
import mkt
CHIPS = '/mnt/project-files/research/formulas_v42/inputs/FF48_chips_vw_daily_20260831.csv'
ER3 = 0.0095 + 0.015                      # same drag as the 3x NDX fund model in the locked engine
_c = {}


def px(key, col=4, f='panel_f32.npz.xz'):
    k = (key, col, f)
    if k not in _c: _c[k] = mkt.pser(key, col, f)
    return _c[k]


def ret(key, idx, f='panel_f32.npz.xz'):
    """daily return of an adjusted close on idx; NaN before the series exists (and on its first day)."""
    p = px(key, 4, f); p = p[~p.index.duplicated()]
    q = p.reindex(idx, method='ffill'); r = q.pct_change()
    r[idx < p.index[0]] = np.nan; r[idx == p.index[0]] = np.nan
    return r.values


def level(key, idx, col=3, f='panel_ext_f32.npz.xz'):
    """a level series (yield, VIX...) known at the close of each day, forward-filled."""
    s = px(key, col, f); s = s[~s.index.duplicated()]
    return s.reindex(idx, method='ffill').values


def chips(idx):
    c = pd.read_csv(CHIPS)
    s = pd.Series(c['Chips'].values / 100.0, index=pd.to_datetime(c['date'].astype(str), format='%Y%m%d'))
    s = s[s > -0.99]
    return s.reindex(idx).values


def semis(idx):
    """semiconductor index daily return: Ken French 'Chips' until SOXX exists, SOXX (adjusted) afterwards."""
    a = chips(idx); b = ret('SOXX', idx)
    return np.where(np.isnan(b), a, b)


def lev3(r, rf, er=ER3): return 3 * r - 2 * rf - er / 252


def fund3(key, base_r, rf, idx):
    """actual 3x fund return where it exists, modelled 3x of base_r before."""
    a = ret(key, idx); m = lev3(np.nan_to_num(base_r, nan=0.0), rf)
    return np.where(np.isnan(a), m, a)
