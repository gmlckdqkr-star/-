"""Price panel loader and tradable sleeves.

Same rules as research/beat_qld/code (data.py + engine.build):
- panel = research/data/panel_f32.npz.xz (daily OHLC, col 4 = close)
- leveraged sleeve before its listing = synthetic L*r_under - (L-1)*rf - ER/252 (label SYN),
  actual ETF return from its first listed day on.
Panel path: env LAB_PANEL, default the shared project folder.
HOLDOUT SEAL: series() drops every row dated after SEAL (2014-12-31) before anything else is derived from it, so
nothing here (build, kr_clean's gap scan, a sleeve's listing date, price_for_signal) depends on later rows.
Row dates = the quoting session's local calendar day (FX bars of the panel are stamped 00:00 London, i.e. 23:00 UTC in
British summer time): every timestamp is read in Europe/London before it is cut to a date (US and KR keys keep their
UTC date: 12:00-14:00 and 00:00 UTC).
"""
import io, lzma, os
import numpy as np, pandas as pd

PANEL = os.environ.get('LAB_PANEL', '/mnt/project-files/research/data/panel_f32.npz.xz')
ER = 0.0095
SEAL = pd.Timestamp('2014-12-31')     # = gates.DEV_END (asserted there); no row after it leaves series()
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
# KR-listed domestic-index ETFs (account: kr_etf only). Own price series, no synthetic history before listing; the
# panel has a long gap in 069500 / 091160 (2007-01 .. 2009-04), so each starts after its last gap > KR_MAX_GAP days (a holiday is at most ~11).
# Prices are put on the _NDX calendar by forward fill (a KR close on a US holiday is carried into the next US day's
# return; nothing is lost). 229200.KS (KOSDAQ150) has no data <= 2014 and is left out.
KR_SLEEVES = {'KR200': '069500.KS', 'KRLEV': '122630.KS', 'KRINV': '114800.KS', 'KRSEMI': '091160.KS'}
KR_MAX_GAP = 20          # > the longest KR holiday (2017 Chuseok, 11 days)
for _n, _k in KR_SLEEVES.items():
    SLEEVES[_n] = (_k, _k, 1)
# KR tax rule (checked 11-03 from 국세청 rulings quoted by kcie/KB/Toss/iM증권; primary 국세청/KRX pages blocked):
# 국내주식형 ETF (KODEX 200, KODEX 반도체) = 매매차익 비과세 -> 0.  KODEX 레버리지/인버스 are legally 기타 ETF
# (보유기간과세 15.4%); their real tax base (과표기준가) is small, but lab books the conservative upper bound
# 15.4% of every sale gain.  Every other sleeve in a kr_etf account stands for a KR-listed overseas-index ETF -> 15.4%.
KR_TAX = {'KR200': 0.0, 'KRSEMI': 0.0, 'KRLEV': 0.154, 'KRINV': 0.154}
# Derived signal series (not ETF panel keys, never on a bar / MS1 path): _SP500EW = the point-in-time equal-weight index
# of S&P 500 members from the sealed stock panel (lab/stocks.py sp500ew: mean close-to-close return of the names that
# were members at t-1 and have a price at t-1 and t; level 1.0 on 1970-01-02, the first point-in-time member day).
# A signal name like _NDX: price / sma / ret / vol / ... read it; series() builds it on the stock calendar (<= SEAL),
# price_for_signal carries it onto a frame's dates (ETF frame: from 1985-10 like any panel key).
SP500EW = '_SP500EW'
DERIVED = (SP500EW,)
_cache = {}


def kr_clean(s):
    """Drop everything up to and including the last calendar gap > KR_MAX_GAP days (a gap return is not a return)."""
    g = s.index.to_series().diff().dt.days
    bad = g[g > KR_MAX_GAP]
    return s[s.index >= bad.index[-1]] if len(bad) else s


def _z():
    if 'z' not in _cache:
        _cache['z'] = np.load(io.BytesIO(lzma.open(PANEL).read()))
    return _cache['z']


def keys():
    """ETF panel keys (the derived signal series DERIVED are not panel keys: signal_keys)."""
    return sorted({k.split('|')[0] for k in _z().files})


def signal_keys():
    """Every name a signal expression may read as a series: the panel keys and the derived series (DERIVED)."""
    return sorted(set(keys()) | set(DERIVED))


def _dates(ts):
    """Unix seconds -> calendar dates of the quoting session (Europe/London wall clock: a KRW_X bar stamped
    2014-07-07 23:00 UTC is the 2014-07-08 London bar; US / KR stamps keep their UTC date)."""
    return pd.to_datetime(ts, unit='s', utc=True).tz_convert('Europe/London').tz_localize(None).normalize()


def series(k, col=4):
    """One panel column on its own dates, rows <= SEAL only (holdout seal: later rows are dropped first). k = _SP500EW
    (DERIVED): the stock panel's equal-weight member index level (lab/stocks.py sp500ew_series, close only)."""
    if k == SP500EW:
        if col != 4:
            raise ValueError(f'{SP500EW} is a close level only (col 4), not col {col}')
        from . import stocks                       # lazy: stocks imports data
        s = stocks.sp500ew_series()
        return s[s.index <= SEAL]
    z = _z()
    d = _dates(z[k + '|ts'])
    s = pd.Series(z[k + '|v'][:, col].astype(float), index=d)
    s = s[s.index <= SEAL]
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
    kr = set(KR_SLEEVES.values())
    F = pd.concat({k: (kr_clean(series(k)) if k in kr else series(k)) for k in need}, axis=1)
    F = F[F.index >= F['_NDX'].first_valid_index()]
    F = F[F['_NDX'].notna()]
    for k in kr & set(F.columns):            # KR prices on the US calendar: carry the last KR close (after its start)
        fv = F[k].first_valid_index()
        if fv is not None:
            F.loc[F.index >= fv, k] = F.loc[F.index >= fv, k].ffill()
    rf = rf_daily(F.index)
    R, SRC = {}, {}
    for n, (etf, u, L) in S.items():
        ru = F[u].pct_change(fill_method=None)
        ra = F[etf].pct_change(fill_method=None)
        first = F[etf].first_valid_index()          # None: not listed on or before SEAL -> synthetic throughout
        if L == 1:
            r = ra.where(ra.notna(), ru)
        else:
            syn = L * ru - (L - 1) * rf - ER / 252.0
            r = syn if first is None else syn.where(F.index <= first, ra)
        R[n] = r
        SRC[n] = first
    R = pd.DataFrame(R)
    R['CASH'] = rf
    out = (F, R, rf, SRC)
    _cache[('build', key)] = out
    return out


MACRO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'macro_flags_le2014.csv.gz')
MACRO_KEYS = ('inv', 'inv2', 'shock', 'shock10', 'shock6m', 'shock6m75', 'shock3m', 'csj')   # MS1 ctx.F keys
MACRO_SPLICE = pd.Timestamp('1986-01-02')     # spx-calendar flags before, ndx-calendar flags from (= MS1 real_ndx)
MACRO_SEAL = SEAL


def macro_table():
    """The 8 MS1 macro warning flags (research/crash_overlay ov.flags_hist) on their historical dates, <= 2014-12-31
    only (file built by tools/build_macro_flags.py). Rows before 1986-01-02 come from the SPX calendar (1928-1985), the
    rest from the NDX calendar (1984-2014, the one MS1's real_ndx_86_14 uses). bool DataFrame indexed by date."""
    if 'macro' not in _cache:
        T = pd.read_csv(MACRO_FILE, parse_dates=['date'])
        if T['date'].max() > MACRO_SEAL:
            raise RuntimeError(f'{MACRO_FILE} has rows after {MACRO_SEAL.date()} (holdout seal)')
        T = T[((T['cal'] == 'spx') & (T['date'] < MACRO_SPLICE)) | ((T['cal'] == 'ndx') & (T['date'] >= MACRO_SPLICE))]
        _cache['macro'] = T.set_index('date')[list(MACRO_KEYS)].astype(bool).sort_index()
    return _cache['macro']


def macro_flags(idx):
    """Flags carried forward onto the dates idx (a lab date takes the latest flag dated on or before it: causal);
    dates before 1928-01-03 -> False. Dates after 2014-12-31 keep the 2014-12-31 value (lab cuts its data there)."""
    T = macro_table()
    return T.reindex(pd.DatetimeIndex(idx), method='ffill').fillna(False).astype(bool)


def price_for_signal(F, name):
    """Signal price. A sleeve name (TQQQ, QLD, QQQ...) means its UNDERLYING index (long history, same as
    the research engines); any other panel key (e.g. _NDX, XLK, KRW_X) is used as is."""
    if name in SLEEVES:
        u = SLEEVES[name][1]
        if u in F.columns:
            return F[u]
        su = kr_clean(series(u)) if u in KR_SLEEVES.values() else series(u)
        return su.reindex(F.index).ffill()
    if name in F.columns:
        return F[name]
    s = series(name)
    return s.reindex(F.index).ffill()
