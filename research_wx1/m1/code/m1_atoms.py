"""M1 atoms: primitive x transform x expanding (past-only) quantile threshold x direction -> int8 day arrays
(1 = true, 0 = false, -1 = unknown). Two era matrices:
  SPX era rows 1954-01-04..1985-12-31 (own index = S&P 500 TR),  NDX era rows 1985-01-02..2014-12-31 (own index =
  Nasdaq-100 price, spliced onto S&P TR before 1985-10-01 only for the long transform windows of C3 price atoms).
Non-C3 atoms are identical in both eras (same calendar date -> same value). C3 family = own-index price transforms,
own realized vol / drawdown, GWZ price-derived (svar, dtoy, dtoat), MS1 macro flags, C3 base signal (bk.C3sig).
Locked with the generator (PRECOMMIT_M1)."""
import os, sys, json, numpy as np, pandas as pd
from numba import njit
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/'
os.environ.setdefault('NUMBA_CACHE_DIR', SCR + 'nb')
QS = (0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9)
TR_D = ('L', 'Z63', 'Z252', 'Z756', 'C5', 'C21', 'C63', 'C252', 'S21', 'S50', 'S100', 'S200')
TR_M = ('L', 'Z252', 'Z756', 'C21', 'C63', 'C252', 'S200')
SLOPE_D = (50, 200); SLOPE_M = (200,)
MINHIST = 504          # transform observations before a threshold is used
SUB = 5                # every 5th past observation enters the expanding-quantile sample
SPX_ROWS = ('1954-01-04', '1985-12-31'); NDX_ROWS = ('1985-01-02', '2014-12-31')
DROP = ('gwz_csp', 'oil_yoy')      # end before 2014 (csp 2003-06, OILPRICE 2013-12): unusable in confirmation / real use


@njit(cache=True)
def expq(y, qs, minhist, sub):
    """thresholds Q[t, j] = quantile qs[j] of the (sub-sampled) finite values of y strictly before t."""
    n = y.shape[0]; nq = qs.shape[0]
    Q = np.full((n, nq), np.nan)
    buf = np.empty(n // sub + 2); m = 0; seen = 0
    for t in range(n):
        if seen >= minhist and m > 10:
            for j in range(nq):
                pos = qs[j] * (m - 1); lo = int(np.floor(pos)); fr = pos - lo
                hi = min(lo + 1, m - 1)
                Q[t, j] = buf[lo] * (1 - fr) + buf[hi] * fr
        x = y[t]
        if np.isfinite(x):
            if seen % sub == 0:
                # insertion into sorted buf[0:m]
                i = m
                while i > 0 and buf[i - 1] > x:
                    buf[i] = buf[i - 1]; i -= 1
                buf[i] = x; m += 1
            seen += 1
    return Q


def roll_mean(x, n): return pd.Series(x).rolling(n, min_periods=n).mean().values
def roll_std(x, n): return pd.Series(x).rolling(n, min_periods=n).std().values
def shift(x, n):
    o = np.full_like(x, np.nan); o[n:] = x[:-n]; return o


def transforms(x, kind, freq):
    base = np.log(np.where(x > 0, x, np.nan)) if kind == 'pos' else x.astype(float)
    out = {}
    trs = TR_D if freq in ('d', 'w') else TR_M
    for tr in trs:
        if tr == 'L': y = base
        elif tr[0] == 'Z':
            n = int(tr[1:]); sd = roll_std(base, n); y = (base - roll_mean(base, n)) / np.where(sd > 0, sd, np.nan)
        elif tr[0] == 'C': n = int(tr[1:]); y = base - shift(base, n)
        elif tr[0] == 'S': n = int(tr[1:]); y = base - roll_mean(base, n)
        out[tr] = y
    sl = {}
    for n in (SLOPE_D if freq in ('d', 'w') else SLOPE_M):
        s = roll_mean(base, n); sl[n] = s - shift(s, 21)
    return out, sl


def atoms_of(name, x, kind, freq, c3):
    """-> list of (atom_meta, int8 array over the full calendar)"""
    res = []
    trs, sl = transforms(x, kind, freq)
    qs = np.array(QS)
    for tr, y in trs.items():
        Q = expq(np.ascontiguousarray(y, dtype=np.float64), qs, MINHIST, SUB)
        ok = np.isfinite(y)
        for j, q in enumerate(QS):
            th = Q[:, j]; av = ok & np.isfinite(th)
            gt = np.where(av, (y > th).astype(np.int8), np.int8(-1)).astype(np.int8)
            lt = np.where(av, (y <= th).astype(np.int8), np.int8(-1)).astype(np.int8)
            res.append((dict(prim=name, tr=tr, q=q, dir='>', c3=c3), gt))
            res.append((dict(prim=name, tr=tr, q=q, dir='<=', c3=c3), lt))
    for n, s in sl.items():
        ok = np.isfinite(s)
        # slope sign needs MINHIST observations of the SMA too (same warm-up rule)
        cnt = np.cumsum(ok); ok = ok & (cnt > MINHIST)
        res.append((dict(prim=name, tr='SL%d' % n, q=0.0, dir='>', c3=c3), np.where(ok, (s > 0).astype(np.int8), np.int8(-1)).astype(np.int8)))
        res.append((dict(prim=name, tr='SL%d' % n, q=0.0, dir='<=', c3=c3), np.where(ok, (s <= 0).astype(np.int8), np.int8(-1)).astype(np.int8)))
    return res


def own_index(R, era):
    """own-index daily simple returns on the full calendar for an era (NaN-free, 0 when absent)."""
    spx = R['SPX'].fillna(0.0).values
    if era == 'spx':
        return spx
    ndx = R['NDX'].values
    start = R.index.searchsorted(pd.Timestamp('1985-10-02'))
    o = spx.copy(); o[start:] = np.nan_to_num(ndx[start:])
    return o


def build():
    sys.path.insert(0, SCR + 'code'); import m1_data as D
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, ov, bk
    R, M = D.cal(); idx = R.index
    z = np.load(SCR + 'cache/prim.npz'); meta = json.load(open(SCR + 'cache/prim_meta.json'))
    rows = {e: (idx.searchsorted(pd.Timestamp(a)), idx.searchsorted(pd.Timestamp(b), side='right')) for e, (a, b) in
            (('spx', SPX_ROWS), ('ndx', NDX_ROWS))}
    AM = []; ARR = {'spx': [], 'ndx': []}

    def push(m, a, era=None):
        if era is None:
            AM.append(dict(m, era='both'))
            for e in ('spx', 'ndx'):
                i0, i1 = rows[e]; ARR[e].append(a[i0:i1])
        else:
            raise RuntimeError
    # shared (era-independent) primitives
    for name, m in meta.items():
        if name in DROP:
            continue
        for am, a in atoms_of(name, z[name], m['kind'], m['freq'], bool(m['c3'])):
            push(am, a)
    # era-specific C3 own-index primitives
    eraC3 = {}
    for e in ('spx', 'ndx'):
        r = own_index(R, e); lv = np.exp(np.cumsum(np.log1p(r)))
        lr = np.log1p(r)
        rv21 = pd.Series(lr).rolling(21).std().values * np.sqrt(252)
        dd = lv / pd.Series(lv).rolling(252, min_periods=1).max().values - 1
        lst = []
        for name, x, kind in (('own_px', lv, 'pos'), ('own_rv21', rv21, 'pos'), ('own_dd252', dd, 'rate')):
            lst += atoms_of(name, x, kind, 'd', True)
        eraC3[e] = lst
    assert [a[0] for a in eraC3['spx']] == [a[0] for a in eraC3['ndx']]
    for k in range(len(eraC3['spx'])):
        AM.append(dict(eraC3['spx'][k][0], era='own'))
        for e in ('spx', 'ndx'):
            i0, i1 = rows[e]; ARR[e].append(eraC3[e][k][1][i0:i1])
    # MS1 macro flags (full 1928-2014 frame, ov.flags_hist as std/lab) - same both eras
    X = pd.DataFrame({'y10': M['y10'].values, 'y3m': M['y3m'].values, 'cs': M['cs'].values}, index=idx)
    F = ov.flags_hist(X)
    for k in F.columns:
        f = F[k].values.astype(np.int8)
        push(dict(prim='macro', tr=k, q=0.0, dir='on', c3=True), f)
        push(dict(prim='macro', tr=k, q=0.0, dir='off', c3=True), (1 - f).astype(np.int8))
    # C3 base signal from std contexts (real_spx_55_85 / real_ndx_86_14), aligned by source row
    C = std.contexts()
    c3m = {}
    for e, bn in (('spx', 'real_spx_55_85'), ('ndx', 'real_ndx_86_14')):
        c = C[bn]; B = bk.C3sig(c)[0]
        src = jp_index(e)                                       # source calendar of that context
        dts = src[c.ii[0]]
        s = pd.Series(B, index=dts).reindex(idx)
        c3m[e] = s.values
    for nm, fn in (('c3on', lambda b: b >= 3 - 1e-9), ('c3any', lambda b: b >= 1 - 1e-9)):
        for dirn, inv in (('on', False), ('off', True)):
            AM.append(dict(prim='c3sig', tr=nm, q=0.0, dir=dirn, c3=True, era='own'))
            for e in ('spx', 'ndx'):
                b = c3m[e]; ok = np.isfinite(b); v = fn(np.nan_to_num(b)); v = (~v) if inv else v
                a = np.where(ok, v.astype(np.int8), np.int8(-1)).astype(np.int8)
                i0, i1 = rows[e]; ARR[e].append(a[i0:i1])
    out = {}
    for e in ('spx', 'ndx'):
        A = np.ascontiguousarray(np.vstack(ARR[e]).astype(np.int8)); out[e] = A
        i0, i1 = rows[e]
        np.save(SCR + 'cache/atoms_%s.npy' % e, A)
        np.save(SCR + 'cache/dates_%s.npy' % e, idx.values[i0:i1].astype('datetime64[D]').astype(np.int64))
    json.dump(AM, open(SCR + 'cache/atoms_meta.json', 'w'))
    return AM, out


_JP = {}
def jp_index(e):
    import jp
    if e not in _JP:
        if e == 'spx': R, M = jp.calendar('1928-01-03', '1985-12-31')
        else: R, M = jp.calendar('1984-01-03', '2014-12-31')
        _JP[e] = R.index
    return _JP[e]


if __name__ == '__main__':
    import time; t = time.time()
    AM, out = build()
    c3 = sum(a['c3'] for a in AM)
    print('atoms', len(AM), 'c3', c3, 'non-c3', len(AM) - c3, {e: a.shape for e, a in out.items()}, '%.0fs' % (time.time() - t))
