"""WX1-M4 MS1 helpers (in-process, read-only use of std.py and lab/lab/ms1eng.py; no lab code edited).
- series_paths(dates, ret): exact re-implementation of lab ms1._Server.series returning the per-path after-tax CAGR
  (fc) per basis, so that a candidate stream and the s0.85 stream can be paired path by path (d_stream).
  Parity with lab ms1.measure_series is tested in m4_parity.py.
- run_ms1eng_real(...): lab's MS1 sleeve kernel (ms1eng.run1, tax 22 %, D 0.25, harvest 3) on a real-history basis
  for multi-product weights (after-tax real-history rows)."""
import os, sys, importlib.util, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
os.environ.setdefault('NUMBA_CACHE_DIR', S + 'nb')
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, jp
WARM = 300; SEAL = pd.Timestamp('2014-12-31')
COST, TAX, D_UNITS = 0.003, 0.22, 2.5e6 / 10e6
BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')
_spec = importlib.util.spec_from_file_location('m4_ms1eng', '/mnt/project-files/research/lab/lab/ms1eng.py')
ms1eng = importlib.util.module_from_spec(_spec); sys.modules['m4_ms1eng'] = ms1eng; _spec.loader.exec_module(ms1eng)
assert ms1eng.WARM == WARM
_X = {}


def frames():
    if not _X:
        R, M = jp.calendar('1984-01-03', '2014-12-31'); _X['ndx'] = jp.mkX(R, M, 'NDX')
        R, M = jp.calendar('1928-01-03', '1985-12-31'); _X['spx'] = jp.mkX(R, M, 'SPX')
        a, b = std.iv.POOLS['dev250'][:2]
        R, M = jp.calendar(a, b); _X['dev'] = jp.mkX(R, M, 'NDX')
    return _X


SRC = {'dev250_path': 'dev', 'dev250_glued': 'dev', 'real_ndx_86_14': 'ndx', 'real_spx_55_85': 'spx', 'real_spx_70_85': 'spx'}


def series_paths(dates, ret, turnover=1.0, min_cover=0.95):
    """-> dict basis -> dict(fc=per-path after-tax CAGR array, row=std.row stats) or None (coverage < min_cover)"""
    C = std.contexts(); X = frames()
    s = pd.Series(np.asarray(ret, float), index=pd.DatetimeIndex(dates))
    s = s[~s.index.duplicated(keep='last')].sort_index()
    s = s[(s.index <= SEAL) & s.notna()]
    lvl = (1.0 + s).cumprod()
    share = min(1.0, max(0.0, float(turnover)))
    out = {}
    for bn in BASES:
        c = C[bn]; Xb = X[SRC[bn]]
        L = lvl.reindex(Xb.index, method='ffill')
        v = np.array(L / L.shift(1).fillna(1.0) - 1.0, dtype=float); v[0] = 0.0
        have = np.asarray((Xb.index >= s.index[0]) & (Xb.index <= s.index[-1]))
        v = np.where(have, np.nan_to_num(v), 0.0)
        used = c.ii[:, WARM:]
        cover = float(have[used].mean())
        if cover < min_cover:
            out[bn] = None; continue
        Mx = v[c.ii]; Mx[:, 0] = 0.0; Mx = np.ascontiguousarray(Mx[:, WARM:])
        Qx = np.zeros_like(Mx)
        fin, E = ms1eng.series_run(Mx, Qx, share, COST, TAX, D_UNITS)
        yrs = E.shape[1] / 252
        fc = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
        row, _ = std.row(fc, E)
        row['cover'] = cover
        out[bn] = dict(fc=fc, row=row)
    return out


def s085_stream():
    """s0.85 daily after-cost PRE-TAX stream on the real bases (std.engine tax=0 on std.contexts real_spx_55_85 and
    real_ndx_86_14), spliced at 1986-01-02: (dates, ret)."""
    C = std.contexts(); X = frames(); parts = []
    for bn, xk, end in (('real_spx_55_85', 'spx', '1985-12-31'), ('real_ndx_86_14', 'ndx', '2014-12-31')):
        c = C[bn]
        rB, rbf, rbp, rfs = std.s085(c)
        _, EE0 = std.engine(c, rB, rbf, rbp, rfs, tax=0.0)
        e = EE0[0]
        d = X[xk].index.values[c.ii[0, WARM:]]
        r = np.empty_like(e); r[0] = 0.0; r[1:] = e[1:] / e[:-1] - 1
        parts.append(pd.Series(r, index=pd.DatetimeIndex(d)))
    s = pd.concat(parts); s = s[~s.index.duplicated(keep='last')].sort_index()
    return s


def s085_fc(bn):
    """true s0.85 per-path after-tax CAGR (std.engine with path flags) = what measure_series pairs with"""
    C = std.contexts(); c = C[bn]
    rB, rbf, rbp, rfs = std.s085(c)
    fc, EE = std.engine(c, rB, rbf, rbp, rfs)
    return fc


def run_ms1eng(R, CR, W, FORCE, tax=TAX, harvest=3):
    """lab ms1eng.run1 on one path (rows from WARM-300 offset already applied by the caller). -> (fin, E, ntr)"""
    T = R.shape[0]; E = np.zeros(T - WARM)
    fin, ntr = ms1eng.run1(np.ascontiguousarray(R), np.ascontiguousarray(CR), np.ascontiguousarray(W),
                           np.ascontiguousarray(FORCE), 2, COST, tax, D_UNITS, harvest, 1.0, E)
    return fin, E, ntr
