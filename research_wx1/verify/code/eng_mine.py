# verifier's independent re-derivation of M1 screen numbers for a few rules (pure numpy/python, no worker engine)
import numpy as np, pandas as pd, sys, json
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp
W1 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/cache/'
R, M = jp.calendar('1928-01-03', '2014-12-31'); assert R.index.max() <= pd.Timestamp('2014-12-31')
LEV = {0: 3, 1: 2, 2: 1, 3: None, 4: -1}
def prod_ret(code, r, rf):
    L = LEV[code]
    if L is None: return np.maximum(rf - 0.02/252, 0) * (1 - 0.154)
    if L == 1: return r - 0.002/252
    return L*r - (L-1)*rf - 0.0245/252
def val(A, row, t):
    a = [A[k, t] if k >= 0 else None for k in row[:3]]; st = row[3]
    need = {0: 1, 1: 2, 2: 2}.get(st, 3)
    vs = a[:need]
    if any(v < 0 for v in vs): return -1
    b = [v == 1 for v in vs]
    e = {0: lambda: b[0], 1: lambda: b[0] and b[1], 2: lambda: b[0] or b[1], 3: lambda: all(b), 4: lambda: any(b),
         5: lambda: (b[0] and b[1]) or b[2], 6: lambda: (b[0] or b[1]) and b[2]}[st]()
    return int(e)
def sim(A, r, rf, row):
    T = A.shape[1]; on, off, h = row[4], row[5], row[6]
    dec = np.empty(T, int); cur = 2; last_switch = -10**9; was_active = False
    for t in range(T):
        v = val(A, row, t)
        if v < 0:
            if cur != 2: cur = 2; last_switch = t
            was_active = False
        else:
            want = on if v == 1 else off
            if want != cur and ((not was_active) or (t - last_switch >= h)):
                cur = want; last_switch = t
            was_active = True
        dec[t] = cur
    P = {c: prod_ret(c, r, rf) for c in range(5)}
    nonc = lambda c: 0 if c == 3 else 1
    g = np.zeros(T)
    for i in range(T):
        p = dec[i-3] if i >= 3 else 2
        x = np.log1p(P[p][i])
        if i + 1 < T:
            pn = dec[i-2] if i >= 2 else 2
            if pn != p: x += np.log1p(-0.003*(nonc(p) + nonc(pn)))
        g[i] = x - np.log1p(P[2][i])
    return dec, g
D = np.load(W1+'D.npy', mmap_mode='r'); rules = np.load(W1+'rules.npy'); S = np.load(W1+'S.npy')
res = {}
for e, col, a, b, m0 in (('spx', 'SPX', '1955-01-03', '1985-12-31', 0), ('ndx', 'NDX', '1986-01-02', '1999-12-31', 372)):
    dts = pd.to_datetime(np.load(W1+'dates_%s.npy' % e).astype('datetime64[D]'))
    A = np.load(W1+'atoms_%s.npy' % e, mmap_mode='r')
    pos = R.index.get_indexer(dts); r = R[col].fillna(0.0).values[pos]; rf = M['rf'].values[pos]
    w1 = dts.searchsorted(pd.Timestamp(b), side='right')        # stop at window end (no 2000+ needed)
    for rid in (237118, 214645, 1744, 158736, 6914, 126171):
        row = rules[rid]
        dec, g = sim(np.asarray(A[:, :w1]), r[:w1], rf[:w1], row)
        gs = pd.Series(g, index=dts[:w1]).loc[a:b]
        mon = gs.groupby([gs.index.year, gs.index.month]).sum().values
        Dw = np.asarray(D[rid, m0:m0+len(mon)])
        res.setdefault(rid, {})[e] = dict(max_abs_month_diff=float(np.abs(mon - Dw).max()), sum_mine=float(gs.sum()),
                                          sum_worker=float(S[rid, 0 if e == 'spx' else 4]), ann_mine=float(gs.mean()*252))
for k, v in res.items(): print(k, v)
