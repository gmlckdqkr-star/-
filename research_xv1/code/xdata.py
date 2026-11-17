"""Registered extra inputs for XV1 candidates, aligned to a calendar index (the evaluator's calendar rows).

Names:  'ret:KEY'        daily ratio of the adjusted close of a panel series minus 1 (NaN before the series exists)
        'ret:KEY@ext'    the same from panel_ext_f32
        'lvl:KEY@ext'    a level known at the close of each day (yield, VIX ...), panel_ext_f32 column 3
        'lvl:KEY'        the same from panel_f32
        'chips'          Ken French 'Chips' industry daily return (1926 .. 2026-08-31)
        'kf:COL'         Ken French daily value-weighted return of one of BusEq Enrgy Money Hlth Utils NoDur Manuf Shops Telcm
                         (12-industry set) or of the size groups 'Lo 20', 'Lo 10', 'Qnt 2'
        'cal:month'      calendar month 1..12 of the row;  'cal:dom' day of the month;  'cal:dow' weekday (Monday 0);
        'cal:ymod4'      calendar year modulo 4. Periodic fields only: no absolute date or year is ever handed out.
        'semis'          semiconductor index daily return: 'chips' until SOXX exists, SOXX (adjusted) afterwards
A value is carried forward at most 5 calendar rows; beyond that it is NaN.

The arrays are FULL (they include sealed days). They are only for candidate code and the engine inside the evaluator:
never print, plot or save them."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
sys.path.insert(0, '/mnt/project-files/research/c3_multi/code')
import mkt, md
CHIPS = '/mnt/project-files/research/formulas_v42/inputs/FF48_chips_vw_daily_20260831.csv'
ER3 = 0.0095 + 0.015                      # same yearly drag as the 3x NDX fund model of the locked engine
CARRY = 5
_c = {}


def px(key, col=4, f='panel_f32.npz.xz'):
    k = (key, col, f)
    if k not in _c:
        s = mkt.pser(key, col, f); _c[k] = s[~s.index.duplicated()]
    return _c[k]


def _file(tag): return 'panel_ext_f32.npz.xz' if tag == 'ext' else 'panel_f32.npz.xz'


def ret(key, idx, f='panel_f32.npz.xz'):
    """daily return of an adjusted close on idx; NaN before the series exists, on its first day and where it is stale."""
    p = px(key, 4, f)
    if not len(p): return np.full(len(idx), np.nan)
    q = p.reindex(idx).ffill(limit=CARRY); r = q.pct_change(fill_method=None)
    r[idx <= p.index[0]] = np.nan
    return r.values


def level(key, idx, col=3, f='panel_ext_f32.npz.xz'):
    return px(key, col, f).reindex(idx).ffill(limit=CARRY).values


def read_chips():
    """raw reader of the Ken French 'Chips' file (date-indexed daily returns)"""
    c = pd.read_csv(CHIPS)
    s = pd.Series(c['Chips'].values / 100.0, index=pd.to_datetime(c['date'].astype(str), format='%Y%m%d'))
    return s[s > -0.99]


def chips(idx):
    if 'chips' not in _c: _c['chips'] = read_chips()
    return _c['chips'].reindex(idx).values


def semis(idx):
    a = chips(idx); b = ret('SOXX', idx)
    return np.where(np.isnan(b), a, b)


def kfret(col, idx):
    if 'kf' not in _c: _c['kf'] = md.kf()
    return _c['kf'][col].reindex(idx).values


def cal(field, idx):
    if field == 'month': return np.asarray(idx.month, dtype=np.float64)
    if field == 'dom': return np.asarray(idx.day, dtype=np.float64)
    if field == 'dow': return np.asarray(idx.dayofweek, dtype=np.float64)
    if field == 'ymod4': return np.asarray(idx.year % 4, dtype=np.float64)
    raise KeyError(field)


def get(name, idx):
    if name == 'chips': return chips(idx)
    if name == 'semis': return semis(idx)
    kind, rest = name.split(':', 1); key, _, tag = rest.partition('@')
    if kind == 'kf': return kfret(rest, idx)
    if kind == 'cal': return cal(rest, idx)
    if kind == 'ret': return ret(key, idx, _file(tag))
    if kind == 'lvl': return level(key, idx, 3, _file(tag))
    raise KeyError(name)


def lev3(r, rf, er=ER3):
    """modelled 3x daily-reset fund on a 1x return series"""
    return 3 * r - 2 * rf - er / 252


def spliced3(actual, base_r, rf):
    """actual 3x fund return where it exists, modelled 3x of base_r before (NaN where neither exists)."""
    return np.where(np.isnan(actual), lev3(base_r, rf), actual)
