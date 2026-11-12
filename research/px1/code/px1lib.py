"""PX1 library: market builders (AT2 5 + Japan) and the 270 pre-registered rules (PRECOMMIT_PX1.md)."""
import os, sys, numpy as np, pandas as pd, itertools
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/nbc'
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import ov, mkt, rx
AD = '/mnt/project-files/research/at2/data/'; QD = '/mnt/project-files/research/q1_alarm/data/'
CC = {'UK': 'GB', 'CA': 'CA', 'AU': 'AU', 'DE': 'DE', 'FR': 'FR'}
DIV = {'UK': 0.035, 'CA': 0.025, 'AU': 0.040, 'FR': 0.030, 'JP': 0.012, 'DE': 0.0}
def _monthly(path, col, idx):
    f = pd.read_csv(path, parse_dates=['observation_date']).set_index('observation_date')[col].dropna()
    f.index = f.index + pd.offsets.MonthBegin(1)
    return f.reindex(idx.union(f.index)).ffill().reindex(idx)
def _finish(X, div):
    ok = X[['y3m', 'y10']].notna().all(axis=1); pos = X.index.get_loc(ok.idxmax())
    X[['y3m', 'y10']] = X[['y3m', 'y10']].fillna(0.0)
    X['r'] = X['r'] + div / 252; X['rf'] = X['y3m'] / 100 / 252; X['cs'] = 0.0; X['vix'] = np.nan
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    return X, max(0, pos + 378 - ov.WARM)
def build(m, div=True):
    d = DIV[m] if div else 0.0
    if m == 'JP':
        s = pd.read_csv(QD + 'NIKKEI225_le2014.csv', parse_dates=['observation_date']).set_index('observation_date')['NIKKEI225'].dropna()
        X = pd.DataFrame(index=s.index); X['r'] = s.pct_change().fillna(0.0)
        g = pd.read_csv(QD + 'mof_jgb_le2014.csv', skiprows=1); g['Date'] = pd.to_datetime(g['Date'], format='%Y/%m/%d')
        y = pd.to_numeric(g.set_index('Date')['10Y'], errors='coerce').dropna()
        X['y10'] = y.reindex(X.index.union(y.index)).ffill().reindex(X.index).shift(1)    # yesterday's close yield
        X['y3m'] = _monthly(QD + 'IR3TCD01JPM156N_le2014.csv', 'IR3TCD01JPM156N', X.index)
        X = X[X.index >= '1979-01-01']
        return _finish(X, d)
    s = pd.read_csv(AD + '%s_index_le2014.csv' % m, parse_dates=['date']).set_index('date')['close']
    X = pd.DataFrame(index=s.index); X['r'] = s.pct_change().fillna(0.0)
    X['y3m'] = _monthly(AD + 'IR3TIB01%sM156N_le2014.csv' % CC[m], 'IR3TIB01%sM156N' % CC[m], X.index)
    X['y10'] = _monthly(AD + 'IRLTLT01%sM156N_le2014.csv' % CC[m], 'IRLTLT01%sM156N' % CC[m], X.index)
    return _finish(X, d)
def ctx(X, i0):
    c = ov.Ctx(X, ov.flags_hist(X), np.arange(i0, len(X))[None, :]); return prep(c)
def prep(c):
    c.F['one'] = np.ones(c.r.shape, bool); c.F['none'] = np.zeros(c.r.shape, bool); return c
# ---------------- rules
COND = {'never': ('none',), 'inv': ('inv',), 'shock6m': ('shock6m',), 'alarm': ('inv', 'shock6m'), 'always': ('one',)}
def specs():
    S = []
    for L, vc, k, cau, sl, bd in itertools.product((2, 3), (.30, .40, .50), COND, (None, 'shock6m'), (100, 200), (0.0, .02)):
        S.append(('F1', L, vc, k, cau, sl, bd))
    for n, L, k in itertools.product((63, 126, 252), (2, 3), ('always', 'alarm')): S.append(('F2', n, L, k))
    for th, ma, L in itertools.product((.10, .15, .20), (50, 200), (2, 3)): S.append(('F3', th, ma, L))
    for tg, k in itertools.product((.40, .60, .80), ('always', 'alarm')): S.append(('F4', tg, k))
    return S
V1 = ('F1', 3, .40, 'alarm', 'shock6m', 200, .02)
def vcap(c, L, vc=0.40): return np.where(c.vol(20) > vc, min(1.0, L), float(L))
def signal(c, s):
    f = s[0]
    if f == 'F1':
        _, L, vc, k, cau, sl, bd = s; B = vcap(c, L, vc)
        if cau: B = np.where(ov.macro_cond(c, (cau,)), np.minimum(B, 1.0), B)
        off = ov.trend_gate(c, sl, bd, ov.macro_cond(c, COND[k])); return np.where(off, 0.0, B)
    if f == 'F2':
        _, n, L, k = s; lv = c.lvl; crf = np.cumsum(c.rf, axis=1)
        mom = np.full(lv.shape, np.nan); mom[:, n:] = lv[:, n:] / lv[:, :-n] - 1 - (crf[:, n:] - crf[:, :-n])
        bad = ~(mom > 0) & ov.macro_cond(c, COND[k]); return np.where(bad, 0.0, vcap(c, L))
    if f == 'F3':
        _, th, ma, L = s; hi = pd.DataFrame(c.lvl.T).rolling(252, min_periods=1).max().values.T
        dd = c.lvl / hi - 1; off = ov.hyst((c.lvl > c.sma(ma)) & (dd > -th), dd <= -th); return np.where(off, 0.0, vcap(c, L))
    if f == 'F4':
        _, tg, k = s; B = np.minimum(3.0, tg / np.maximum(c.vol(20), 1e-6)); B = np.where(np.isnan(B), 1.0, B)
        off = ov.trend_gate(c, 200, .02, ov.macro_cond(c, COND[k])); return np.where(off, 0.0, B)
def run(c, s, **kw):
    cg, E = std.engine(c, signal(c, s), rx.av23s, rx.P_av23s(.85), 0.1, cspr=10.0, **kw); return cg, E
