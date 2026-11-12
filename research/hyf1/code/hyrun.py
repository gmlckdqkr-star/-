"""HYF1 runner (PRECOMMIT_HYF1.md): v1 idle share -> HY (trend gate, month-end decisions) on the user_port_up MS1 engine, cash 0. <=2014 ONLY."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/user_port_up/code'); sys.path.insert(0, '/mnt/project-files/research/vxr1/code')
import uprun as U, upeng as E, updata as UD
WARM = E.WARM
PRODS = E.PRODS + ['HY']; J = {n: i for i, n in enumerate(PRODS)}; NJ = len(PRODS)
NOTAX = np.array([n == 'CASH' for n in PRODS])
DD = '/mnt/project-files/research/hyf1/data/'
END = pd.Timestamp('2014-12-31'); _C = {}

def hy_bydate(bn, fee=0.008, desmooth=False, hyg=False):
    """(r, do, monthend flag) by date on the X table of basis bn"""
    dates, X = UD.basis_dates()[bn]
    V = pd.read_csv(DD + 'vwehx_le2014.csv', parse_dates=['date']).set_index('date')
    r = V['adjclose'].pct_change(); dist = (V['div'] / V['close'].shift(1)).fillna(0.0)
    if desmooth:
        r = (r - 0.36 * r.shift(1)) / (1 - 0.36)
    r = r.reindex(dates).fillna(0.0) - fee / 252; do = dist.reindex(dates).fillna(0.0)
    if hyg:
        H = pd.read_csv(DD + 'hyg_le2014.csv', parse_dates=['date']).set_index('date')
        rh = H['adjclose'].pct_change(); dh = (H['div'] / H['close'].shift(1)).fillna(0.0)
        m = (dates > H.index[0]) & (dates <= END)
        r = r.where(~m, rh.reindex(dates)); do = do.where(~m, dh.reindex(dates).fillna(0.0)); r = r.fillna(0.0)
    s = pd.Series(dates, index=dates); me = (s.dt.month != s.shift(-1).dt.month).values
    rg = V['adjclose'].pct_change().reindex(dates).fillna(0.0)      # gate always reads the published VWEHX series
    return r.values, do.values, me, rg.values

def products(bn, **kw):
    key = ('p', bn) + tuple(sorted(kw.items()))
    if key in _C: return _C[key]
    b = U.basis(bn); c = b['c']; r0, dg0, do0 = U.prod(bn); P, T, _ = r0.shape
    r = np.zeros((P, T, NJ)); dg = np.zeros_like(r); do = np.zeros_like(r)
    r[:, :, :len(E.PRODS)] = r0; dg[:, :, :len(E.PRODS)] = dg0; do[:, :, :len(E.PRODS)] = do0
    r[:, :, J['CASH']] = 0.0
    rh, dh, me, rg = hy_bydate(bn, **kw)
    r[:, :, J['HY']] = rh[c.ii]; do[:, :, J['HY']] = dh[c.ii]
    r[:, 0, :] = 0; dg[:, 0, :] = 0; do[:, 0, :] = 0
    _C[key] = (r, dg, do, me[c.ii], rg[c.ii]); return _C[key]

def gate(bn, n, avg5, delay=2):
    r, dg, do, me, rg = products(bn); P, T = rg.shape
    px = np.cumprod(1 + rg, axis=1)
    pxs = pd.DataFrame(px.T)
    sig = pxs.rolling(5).mean() if avg5 else pxs
    on = (sig > pxs.rolling(n).mean()).values.T.astype(float); on[:, :n] = 0
    st = np.zeros_like(on)
    for p in range(P):
        cur = 0.0
        for t in range(T):
            if me[p, t]: cur = on[p, t]
            st[p, t] = cur
    lag = np.zeros_like(st); lag[:, delay:] = st[:, :-delay]
    return lag[:, WARM:]

def run(bn, n=None, avg5=False, cmul=1.0, gdelay=2, fee=0.008, desmooth=False, hyg=False):
    r, dg, do, me, rg = products(bn, fee=fee, desmooth=desmooth, hyg=hyg); P, T, _ = r.shape; K = T - WARM
    L = U.s085_levels(bn, 2); G = gate(bn, n, avg5, gdelay) if n else None
    out = np.zeros((P, 7)); C = np.zeros((P, K))
    for p in range(P):
        lv = L[p]; W = np.zeros((K, NJ)); W[:, J['TQQQ']] = lv / 3; idle = 1 - lv / 3
        if n: W[:, J['HY']] = idle * G[p]; W[:, J['CASH']] = idle * (1 - G[p])
        else: W[:, J['CASH']] = idle
        fl = np.r_[True, (np.abs(np.diff(W, axis=0)) > 1e-12).any(axis=1)]
        E.run_port(np.ascontiguousarray(r[p, WARM:]), np.ascontiguousarray(dg[p, WARM:]), np.ascontiguousarray(do[p, WARM:]),
                   W[None], fl[None], np.array([1.0]), np.zeros(K, bool), 0.0, NOTAX, 0.003 * cmul, 0.22, 0.25, 0.154, out[p], C[p])
    yrs = K / 252; cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    return dict(cagr=cg, mdd=out[:, 1], E7=out[:, 2], E12=out[:, 3], ntr=out[:, 4] / yrs, cost=out[:, 5], curve=C)

def window(res, a, b='2014-12-31', bn='real_ndx_86_14'):
    c = U.basis(bn)['c']; dates, X = UD.basis_dates()[bn]; d = dates[c.ii[0, WARM:]]; C = res['curve'][0]
    i0 = int(np.searchsorted(d, pd.Timestamp(a))) - 1; i1 = int(np.searchsorted(d, pd.Timestamp(b), side='right')) - 1
    return float((C[i1] / C[i0]) ** (252 / (i1 - i0)) - 1)
