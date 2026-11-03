"""Price panel loader and tradable sleeves.

Same rules as research/beat_qld/code (data.py + engine.build):
- panel = research/data/panel_f32.npz.xz (daily OHLC, col 4 = close)
- leveraged sleeve before its listing = synthetic L*r_under - (L-1)*rf - ER/252 (label SYN),
  actual ETF return from its first listed day on.
Panel path: env LAB_PANEL, default the shared project folder.
"""
import io, lzma, os
import numpy as np, pandas as pd

PANEL = os.environ.get('LAB_PANEL', '/mnt/project-files/research/data/panel_f32.npz.xz')
ER = 0.0095
# name: (actual etf, underlying for synthetic part, leverage)
SLEEVES = {
    'QLD': ('QLD', '_NDX', 2), 'TQQQ': ('TQQQ', '_NDX', 3), 'SOXL': ('SOXL', 'SOXX', 3),
    'USD': ('USD', 'SOXX', 2), 'TECL': ('TECL', 'XLK', 3), 'UPRO': ('UPRO', 'SPY', 3),
    'SSO': ('SSO', 'SPY', 2), 'TMF': ('TMF', 'TLT', 3), 'UBT': ('UBT', 'TLT', 2),
    'UGL': ('UGL', 'GLD', 2), 'FAS': ('FAS', 'XLF', 3), 'ERX': ('ERX', 'XLE', 3),
    'CURE': ('CURE', 'XLV', 3), 'TNA': ('TNA', 'IWM', 3), 'DRN': ('DRN', 'IYR', 3),
    'LABU': ('LABU', 'XBI', 3),
    'QQQ': ('QQQ', '_NDX', 1), 'SPY': ('SPY', 'SPY', 1), 'TLT': ('TLT', 'TLT', 1),
    'GLD': ('GLD', 'GLD', 1), 'IEF': ('IEF', 'IEF', 1), 'SHY': ('SHY', 'SHY', 1),
}
_cache = {}


def _z():
    if 'z' not in _cache:
        _cache['z'] = np.load(io.BytesIO(lzma.open(PANEL).read()))
    return _cache['z']


def keys():
    return sorted({k.split('|')[0] for k in _z().files})


def series(k, col=4):
    z = _z()
    d = pd.to_datetime(z[k + '|ts'], unit='s').normalize()
    s = pd.Series(z[k + '|v'][:, col].astype(float), index=d)
    s = s[~s.index.duplicated(keep='last')].dropna()
    return s[s > 0]


def rf_daily(idx):
    irx = series('_IRX', 3) / 100.0
    return irx.reindex(idx).ffill().fillna(0.0) / 252.0


def build(sleeves=None):
    """Returns (F prices aligned on _NDX calendar, R daily sleeve returns incl. CASH, rf, src first-actual dates)."""
    key = tuple(sorted(sleeves)) if sleeves else None
    if ('build', key) in _cache:
        return _cache[('build', key)]
    S = {n: SLEEVES[n] for n in (sleeves or SLEEVES)}
    need = sorted({v[0] for v in S.values()} | {v[1] for v in S.values()} | {'_NDX'})
    F = pd.concat({k: series(k) for k in need}, axis=1)
    F = F[F.index >= F['_NDX'].first_valid_index()]
    F = F[F['_NDX'].notna()]
    rf = rf_daily(F.index)
    R, SRC = {}, {}
    for n, (etf, u, L) in S.items():
        ru = F[u].pct_change(fill_method=None)
        ra = F[etf].pct_change(fill_method=None)
        first = F[etf].first_valid_index()
        if L == 1:
            r = ra.where(ra.notna(), ru)
        else:
            syn = L * ru - (L - 1) * rf - ER / 252.0
            r = syn.where(F.index <= first, ra)
        R[n] = r
        SRC[n] = first
    R = pd.DataFrame(R)
    R['CASH'] = rf
    out = (F, R, rf, SRC)
    _cache[('build', key)] = out
    return out


def price_for_signal(F, name):
    """Signal price. A sleeve name (TQQQ, QLD, QQQ...) means its UNDERLYING index (long history, same as
    the research engines); any other panel key (e.g. _NDX, XLK, KRW_X) is used as is."""
    if name in SLEEVES:
        u = SLEEVES[name][1]
        return F[u] if u in F.columns else series(u).reindex(F.index).ffill()
    if name in F.columns:
        return F[name]
    s = series(name)
    return s.reindex(F.index).ffill()
