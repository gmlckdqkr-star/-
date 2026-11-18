"""DF5 worlds and assets (<=2014 only). Worlds: P (dev250_path), X (DF3 crash-free world, identical construction), P125 (dev125 pool),
REAL (real_ndx_86_14), S29 (real S&P 1929-54, LH1 fill A), S55 (real S&P 1955-85), OLD (old250 S&P 1928-85 bootstrap).
Each world: dict with the dfe market dict 'm' (r rf rb cpn idxup bondup vol20 st_v1 ...), 'ii' (P,T) source-row index, 'src' (source frame with
all extra columns aligned to the source calendar), 'lvl' (path index level), and helpers. Extra asset returns are mapped by ii."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
END = pd.Timestamp('2014-12-31'); BLK = 250; W = ov.WARM
EX10 = 1.3988294390226633e-4
DATA = '/mnt/project-files/research/df5/data/'

def _src(a, b, s):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, s); assert X.index.max() <= END
    S = pd.concat([R, M.add_prefix('M_')], axis=1); S = S.loc[X.index]
    return X, S

def _xworld(X, P, seed=7, sym=False):
    lv = np.cumprod(1 + X['r'].fillna(0).values); Dd = X.index; n = len(X)
    pos = lambda d: int(Dd.searchsorted(pd.Timestamp(d)))
    amax = lambda x, y: pos(x) + int(np.argmax(lv[pos(x):pos(y)])); amin = lambda x, y: pos(x) + int(np.argmin(lv[pos(x):pos(y)]))
    tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
    pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
    pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
    excl = np.zeros(n, bool)
    for p_, t_ in ((pk1, tr1), (pk2, tr2), (pk3, tr3)): excl[max(p_ - (BLK if sym else 0), 0):min(t_ + BLK, n - 1) + 1] = True
    starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
    T = W + 30 * 252; nb = T // BLK + 1
    g = np.random.default_rng(seed); st = starts[g.integers(0, len(starts), (P, nb))]
    return (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T], len(starts)

_WORLDS = {}
def world(name):
    if name in _WORLDS: return _WORLDS[name]
    if name in ('P', 'X', 'P125', 'XSYM', 'P500'):
        a, b, P, blk, seed = iv.POOLS['dev250']; X, S = _src(a, b, 'NDX'); F = ov.flags_hist(X)
        if name == 'P':
            c = std.contexts()['dev250_path']; m = DC.market('dev250_path')
        else:
            if name == 'X':
                ii, ns = _xworld(X, P); assert ns == 4645
            elif name == 'XSYM':
                ii, ns = _xworld(X, P, sym=True)
            elif name == 'P500':
                a2, b2, P2, blk2, seed2 = iv.POOLS['dev500']; ii = ov.boot_idx(len(X), P=P2, years=30, block=blk2, seed=seed2, lo=1)
            else:
                a2, b2, P2, blk2, seed2 = iv.POOLS['dev125']; ii = ov.boot_idx(len(X), P=P2, years=30, block=blk2, seed=seed2, lo=1)
            c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}; m = DC._finish(c, X)
    elif name == 'REAL':
        X, S = _src('1984-01-03', '2014-12-31', 'NDX'); c = std.contexts()['real_ndx_86_14']; m = DC.market('real_ndx_86_14')
    elif name == 'S55':
        X, S = _src('1928-01-03', '1985-12-31', 'SPX'); c = std.contexts()['real_spx_55_85']; m = DC.market('real_spx_55_85')
    elif name == 'S29':
        m = DC.market('real_spx_29_54'); c = m['ctx']; X = None
        X0, S0 = _src('1928-01-03', '1985-12-31', 'SPX'); idx = m['X_index']
        S = S0.reindex(idx); X = X0.reindex(idx)
    elif name == 'OLD':
        a, b, P, blk, seed = iv.POOLS['old250']; X, S = _src(a, b, 'SPX'); F = ov.flags_hist(X)
        ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=seed, lo=1); c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
        m = DC._finish(c, X)
    else:
        raise KeyError(name)
    w = dict(name=name, m=m, ii=np.asarray(c.ii), S=S, X=X, ctx=c)
    w['lvl'] = np.cumprod(1 + np.nan_to_num(m['r']), axis=1)
    _WORLDS[name] = w
    return w

def col(w, series):
    """map a source-calendar series (pd.Series on w['S'].index) onto the world's paths"""
    a = series.reindex(w['S'].index).values.astype(float)
    return a[w['ii']]

def cut(w, h):
    """horizon cut of a world's market dict (signals are causal, so slicing equals re-building the cut context)"""
    Th = W + h * 252; m = w['m']
    return {k: (v[:, :Th] if isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] >= Th else v) for k, v in m.items()}

def roll_mean(a, n):
    c = np.cumsum(np.nan_to_num(a), axis=1); out = np.full(a.shape, np.nan)
    out[:, n - 1:] = (c[:, n - 1:] - np.concatenate([np.zeros((a.shape[0], 1)), c[:, :-n]], axis=1)) / n
    return out
def roll_std(a, n):
    m1 = roll_mean(a, n); m2 = roll_mean(a * a, n); return np.sqrt(np.maximum(m2 - m1 * m1, 0) * n / max(n - 1, 1))
def roll_max(a, n):
    return pd.DataFrame(a.T).rolling(n, min_periods=1).max().values.T
