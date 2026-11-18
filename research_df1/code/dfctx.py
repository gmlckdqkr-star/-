"""DF1 market contexts (<=2014 only). Selection bases: dev250_path, real_ndx_86_14, real_spx_29_54 (LH1 build, fill A).
Validation: real_spx_55_85, real_spx_70_85 (MS1), UK CA AU DE FR JP (PX1 builders). Upper bound: dev250_glued.
Each market dict: r rf rb cpn idxup bondup st_v1 st_al vol20 (P,T) + 'ctx' (ov.Ctx for locked-engine references)."""
import os, sys, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
sys.path.insert(0, '/mnt/project-files/research/px1/code'); sys.path.insert(0, '/mnt/project-files/research/lh1/code')
import ov, jp, iv, mkt
import px1lib as PX
import lh1run as LH

V1S = ('F1', 3, .40, 'alarm', 'shock6m', 200, .02)       # v1 skeleton (PX1 check: equals bk.C3sig exactly)
ALS = ('F1', 3, .40, 'always', 'shock6m', 200, .02)       # same, trend exit always obeyed
SEL = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')
VAL = ('real_spx_55_85', 'real_spx_70_85', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP')

def _sma(x, n):
    c = np.cumsum(np.c_[np.zeros(x.shape[0]), x], axis=1); m = (c[:, n:] - c[:, :-n]) / n
    return np.c_[np.full((x.shape[0], n - 1), np.nan), m]

def _finish(c, X):
    PX.prep(c)
    y10 = X['y10'].astype(float).values
    cp_src = np.r_[np.nan, y10[:-1]] / 100.0 / 252.0
    cp = np.nan_to_num(cp_src[c.ii], nan=0.0)
    rb = np.nan_to_num(c.rb.copy(), nan=0.0); rb[:, 0] = 0.0; cp[:, 0] = 0.0
    bl = np.cumprod(1 + rb, axis=1)
    m = dict(r=c.r, rf=c.rf, rb=rb, cpn=cp, idxup=(c.lvl > c.sma(200)), bondup=(bl > _sma(bl, 200)),
             st_v1=PX.signal(c, V1S), st_al=PX.signal(c, ALS), vol20=c.vol(20), ctx=c, X_index=X.index)
    m['idxup'] = np.where(np.isnan(c.sma(200)), False, m['idxup']); m['bondup'] = np.where(np.isnan(_sma(bl, 200)), False, m['bondup'])
    return m

_M = {}
def market(name):
    if name in _M: return _M[name]
    if name in ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'):
        c = std.contexts()[name]
        if name.startswith('dev250'):
            a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
        elif name == 'real_ndx_86_14':
            R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX')
        else:
            R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX')
        assert X.index.max() <= pd.Timestamp('2014-12-31')
        _M[name] = _finish(c, X)
    elif name in ('real_spx_29_54', 'real_spx_29_54_B'):
        X = LH.build(LH.END, 'A' if name == 'real_spx_29_54' else 'B'); F = ov.flags_hist(X)
        c = ov.Ctx(X, F, np.arange(0, len(X))[None, :]); _M[name] = _finish(c, X)
    else:
        X, i0 = PX.build(name); assert X.index.max() <= pd.Timestamp('2014-12-31')
        c = PX.ctx(X, i0); _M[name] = _finish(c, X)
    return _M[name]

def target(m, k, sig, Lmax):
    """pre-brake target exposure (PRECOMMIT section 2): st=3 -> L_on, st=1 -> min(L_on, Lmax/3), st=0 -> 0."""
    st = m['st_v1'] if k == 'v1' else m['st_al']
    if sig is None: Lon = np.full(st.shape, float(Lmax))
    else: Lon = np.minimum(float(Lmax), sig / np.maximum(m['vol20'], 1e-9))
    L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0))
    return np.where(np.isnan(L), 0.0, L)
