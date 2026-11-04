"""BE1 engine: broad-ETF sleeves on the MS1 bases (<=2014). Account = user_port_up upeng.run_port (verified == std for s0.85).
Every asset stream is gathered with the SAME row index c.ii as the MS1 NDX path; signals are computed on the gathered path."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/user_port_up/code')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import std, jp, iv
import upeng as E
import bdata as BD
WARM = E.WARM
CACHE = BD.CACHE
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']
_D = {}

def basis_dates():
    if 'bd' in _D: return _D['bd']
    out = {}
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); out['real_ndx_86_14'] = X.index
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
    out['dev250_glued'] = X.index; out['dev250_path'] = X.index
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX')
    out['real_spx_55_85'] = X.index; out['real_spx_70_85'] = X.index
    _D['bd'] = out; return out

def assets(wide=False):
    a = ['NDX'] + BD.LONG
    return a + BD.WIDE if wide else a

def basis(bn, wide=False):
    key = (bn, wide)
    if key in _D: return _D[key]
    c = std.contexts()[bn]; dates = basis_dates()[bn]; assert len(dates) > c.ii.max()
    D = BD.by_date(actual=True).reindex(dates)
    names = assets(wide); P, T = c.ii.shape
    A = np.full((P, T, len(names)), np.nan)
    A[:, :, 0] = np.asarray(c.r, float) - 0.002 / 252
    for j, n in enumerate(names[1:], 1): A[:, :, j] = D[n].values.astype(float)[c.ii]
    A[:, 0, :] = 0.0
    rf = np.asarray(c.rf, float)
    _D[key] = dict(c=c, A=A, rf=rf, names=names, rN=np.asarray(c.r, float)); return _D[key]

# ---------- s0.85 level (held level in force, MS1 F1) ----------
def s085_levels(bn, delay=2):
    fn = CACHE + 's085_lv_%s_d%d.npy' % (bn, delay)
    if os.path.exists(fn): return np.load(fn)
    c = std.contexts()[bn]; B, bfn, bp, fs = std.s085(c); FEAT = std.bk.features(c)
    L = np.zeros((c.P, c.T - WARM))
    for i in range(c.P):
        st, rec = std.beng.run_path(np.ascontiguousarray(c.r[i]), np.ascontiguousarray(c.rf[i]), np.ascontiguousarray(B[i], dtype=np.float64),
                                    np.ascontiguousarray(FEAT[i]), bfn, bp, fstep=fs, delay=delay)
        L[i] = rec[:, 1]
    np.save(fn, L); return L

# ---------- features on the path ----------
def _cum(A):
    ok = np.isfinite(A); LL = np.cumsum(np.log1p(np.where(ok, A, 0.0)), axis=1); NB = np.cumsum(~ok, axis=1)
    return LL, NB

def window_ret(LL, NB, t, n):
    """total log return over rows (t-n, t]; NaN if any missing or t-n < 0"""
    if t - n < 0: return np.full(LL.shape[::2] if LL.ndim == 3 else LL.shape[0], np.nan)
    v = LL[:, t] - LL[:, t - n]; bad = (NB[:, t] - NB[:, t - n]) > 0
    return np.where(bad, np.nan, v)

def decision_rows(T, step=21):
    return np.arange(WARM - 2, T - 2, step)

def mom_score(LL, NB, t):
    ms = [window_ret(LL, NB, t, n) for n in (63, 126, 252)]
    return np.mean(np.expm1(np.stack(ms)), axis=0)       # (P, NA)

# ---------- products ----------
def products(b, levs=(1,), with_tqqq=False):
    """returns prods list, notax (J,), index J {(asset, L): j}, mk(p) -> (r (T,J), do (T,J)) built per path (memory)"""
    A, rf, names = b['A'], b['rf'], b['names']; P, T, NA = A.shape
    prods = [(n, L) for L in levs for n in names]
    if with_tqqq: prods.append(('TQQQ', 3))
    prods.append(('CASH', 0))
    notax = np.array([p[0] == 'CASH' for p in prods]); J = {p: i for i, p in enumerate(prods)}
    cls = []
    for n in names:
        cl = 'bd' if n in ('TLT', 'IEF', 'SHY', 'TIP', 'LQD', 'HYG', 'EMB', 'AGG') else 'cm' if n in ('DBC', 'SLV', 'USO', 'DBA', 'GLD') else 'eq'
        cls.append(cl)
    def mk(p):
        a = np.nan_to_num(A[p], nan=0.0); f = rf[p]; NJ = len(prods)
        r = np.zeros((T, NJ)); do = np.zeros((T, NJ))
        for (n, L), j in J.items():
            if n == 'CASH': r[:, j] = np.maximum(f - 0.02 / 252, 0.0) * (1 - 0.154); continue
            if n == 'TQQQ': r[:, j] = 3 * b['rN'][p] - 2 * f - 0.0245 / 252; continue
            q = names.index(n); x = a[:, q]
            r[:, j] = x if L == 1 else L * x - (L - 1) * f - (0.0095 + 0.0075 * (L - 1)) / 252
            if L == 1 and cls[q] == 'eq' and n != 'NDX': do[:, j] = 0.02 / 252
            elif L == 1 and cls[q] == 'bd': do[:, j] = np.maximum(f, 0) + (0.01 / 252 if n != 'SHY' else 0.0)
        r[0] = 0; do[0] = 0
        return r, do
    return prods, notax, J, mk

def run(b, W_fn, prods, notax, mk, ws=(1.0,), reb='yearly', cost=0.003, tax=0.22, D=0.25):
    """W_fn(p) -> list of (W (K,J), flag (K,)) one per sleeve"""
    P, T = b['A'].shape[:2]; NJ = len(prods); K = T - WARM; rb = np.zeros(K, bool)
    if reb == 'yearly': rb[252::252] = True
    ws = np.asarray(ws, float); out = np.zeros((P, 7)); C = np.zeros((P, K)); dg = np.zeros((K, NJ))
    for p in range(P):
        sl = W_fn(p); Ws = np.stack([s[0] for s in sl]); Fl = np.stack([s[1] for s in sl])
        r, do = mk(p)
        E.run_port(np.ascontiguousarray(r[WARM:]), dg, np.ascontiguousarray(do[WARM:]), Ws, Fl, ws, rb, 0.0,
                   notax, cost, tax, D, 0.154, out[p], C[p])
    yrs = K / 252; cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    return dict(cagr=cg, mdd=out[:, 1], E7=out[:, 2], E12=out[:, 3], ntr=out[:, 4] / yrs, curve=C)

def row(res, ref=None):
    cg = res['cagr']; m = res['mdd']
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(m)), dd80=float(np.mean(m <= -0.8)),
             dd95=float(np.mean(m <= -0.95)), w7=float(np.median(res['E7'])), w12=float(np.median(res['E12'])), tr=float(np.median(res['ntr'])))
    if ref is not None:
        x = cg - ref['cagr']; d.update(d_ref=float(np.median(x)), pw_ref=float(np.mean(x > 1e-5)))
    return d

def sharpe_from_curve(res, rf_b):
    """after-cost after-tax daily log excess Sharpe of the account curve (path median)"""
    C = res['curve']; lr = np.diff(np.log(np.maximum(C, 1e-12)), axis=1)
    ex = lr - np.log1p(np.maximum(rf_b[:, WARM + 1:WARM + C.shape[1]] - 0.02 / 252, 0) * 0.846)
    s = ex.mean(1) / ex.std(1) * 252 ** .5
    return float(np.median(s))
