"""SL1 mega search (PRECOMMIT_SL1, sha256 52860b50...): BT1 rule forms/atoms, product menu = 5 index products +
25 S&P 500 stock sleeves. Kernels (screen / stats_kernel / row_kernel) are bt1_mega's, unchanged: they are generic in
the product index (LX[p, t], CC[p, q]). Discovery: S&P 1971-01-04..1985-12-31 + NDX 1986-01-02..1999-12-31.
CLI: sl1_mega.py a b [n] [outdir]"""
import os, sys, json, time, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, m1_search as MS, m1_stats as ST, m1_engine as EN
SCR = BM.SCR
SEED = 20261106
DISC = {'spx': ('1971-01-04', '1985-12-31'), 'ndx': ('1986-01-02', '1999-12-31')}
SPX_START = '1970-07-01'                        # state warm-up start of the S&P era slice
NIDX = 5; IDX2 = np.array([0, 1, 2, 3], np.int64)


def sleeves():
    z = np.load(SCR + 'cache/sleeves.npz'); names = [str(x) for x in z['names']]
    d = pd.to_datetime(z['dates'].astype('datetime64[D]'))
    return names, {n: pd.Series(z[n], index=d) for n in names}


def products(E):
    """era -> X (5 + S, T): index products (m1_engine) + sleeve simple returns (1x where a sleeve does not exist)."""
    names, S = sleeves(); out = {}
    for e in ('spx', 'ndx'):
        X = E[e]['X']; rows = [X]
        for n in names:
            s = S[n].reindex(E[e]['dates']).values
            rows.append(np.where(np.isfinite(s), s, X[2])[None, :])
        out[e] = np.ascontiguousarray(np.vstack(rows))
    return names, out


def costc(P):
    nc = np.r_[EN.NONCASH, np.ones(P - NIDX, np.int64)]
    return np.array([[np.log1p(-EN.COST * (nc[a] + nc[b])) if a != b else 0.0 for b in range(P)] for a in range(P)])


def gen_shard(AM, shard, n, P, nsl):
    """same atom/form generator as bt1_mega (shard-0 singles dropped: every SL1 rule must use a sleeve)."""
    K, new, old, c3s, mac, oth = P
    isnew = np.zeros(len(AM), bool); isnew[new] = True
    isc3 = np.array([m['c3'] for m in AM])
    rng = np.random.default_rng([SEED, shard])
    R = np.full((n, BM.NC), -1, np.int32); i = 0; B = 200000
    while i < n:
        m = min(B, (n - i) * 3)
        form = rng.choice(5, size=m, p=[0.30, 0.15, 0.20, 0.15, 0.20])
        nat = np.where(form == 0, rng.integers(1, 4, size=m), np.where(form == 1, 3, np.where(form == 3, 2, rng.choice([3, 5, 7], size=m))))
        u = rng.random((m, 7)); cu = rng.random((m, 7))
        pn = new[rng.integers(len(new), size=(m, 7))]; po = old[rng.integers(len(old), size=(m, 7))]
        pc = np.where(cu < 0.25, c3s[rng.integers(len(c3s), size=(m, 7))], np.where(cu < 0.5, mac[rng.integers(len(mac), size=(m, 7))], oth[rng.integers(len(oth), size=(m, 7))]))
        pick = np.where(u < 0.45, pn, np.where(u < 0.75, po, pc))
        slot = np.arange(7)[None, :] < nat[:, None]
        ks = np.where(slot, K[pick], -np.arange(1, 8)[None, :])
        srt = np.sort(ks, 1); distinct = (np.diff(srt, axis=1) != 0).all(1)
        anynon3 = ((~isc3[pick]) & slot).any(1)
        ok = distinct & anynon3
        st = np.where(nat == 1, 0, np.where(nat == 2, rng.integers(1, 3, size=m), rng.integers(3, 7, size=m)))
        hd = BM.HOLDS[rng.integers(3, size=m)]
        m1 = np.floor(rng.random(m) * nat).astype(np.int64) + 1
        vm1 = np.floor(rng.random(m) * (np.maximum(nat, 2) - 1)).astype(np.int64) + 2
        vm2 = np.floor(rng.random(m) * (vm1 - 1)).astype(np.int64) + 1
        # products
        sA = NIDX + rng.integers(nsl, size=m); sB = NIDX + rng.integers(nsl, size=m); iA = IDX2[rng.integers(4, size=m)]
        ty = rng.random(m)
        c1 = np.where(ty < 0.4, sA, np.where(ty < 0.7, sA, iA)); c2 = np.where(ty < 0.4, sB, np.where(ty < 0.7, iA, sA))
        tri = np.where(rng.random((m, 3)) < 0.6, NIDX + rng.integers(nsl, size=(m, 3)), IDX2[rng.integers(4, size=(m, 3))])
        ok2 = c1 != c2
        ok3 = (tri[:, 0] != tri[:, 1]) & (tri[:, 0] != tri[:, 2]) & (tri[:, 1] != tri[:, 2]) & (tri >= NIDX).any(1)
        for j in np.flatnonzero(ok):
            if i >= n: break
            f = int(form[j]); k = int(nat[j])
            if f in (0, 1, 2) and not ok2[j]: continue
            if f in (3, 4) and not ok3[j]: continue
            row = np.full(BM.NC, -1, np.int32); row[0] = f; row[1:1 + k] = pick[j, :k]; row[14] = hd[j]
            if f == 0: row[8] = st[j]; row[11] = c1[j]; row[12] = c2[j]
            elif f == 1: row[8] = 3; row[11] = c1[j]; row[12] = c2[j]
            elif f == 2: row[8] = k; row[9] = m1[j]; row[11] = c1[j]; row[12] = c2[j]
            elif f == 3: row[8] = 2; row[11], row[12], row[13] = tri[j]
            else: row[8] = k; row[9] = vm1[j]; row[10] = vm2[j]; row[11], row[12], row[13] = tri[j]
            R[i] = row; i += 1
    return R


def describe(AM, row, names):
    lev = {0: '3x', 1: '2x', 2: '1x', 3: 'cash', 4: '-1x'}
    lev.update({NIDX + i: 'STK:' + n for i, n in enumerate(names)})
    def at(i):
        m = AM[i]; q = '' if m['q'] == 0 else '@q%.1f' % m['q']
        return '%s.%s%s%s' % (m['prim'], m['tr'], m['dir'], q)
    f = int(row[0]); a = [at(int(x)) for x in row[1:8] if x >= 0]; h = int(row[14]); L = lambda j: lev[int(row[j])]
    if f == 0: return '%s -> %s / %s, hold %d' % (BM.EN_desc(int(row[8]), a), L(11), L(12), h)
    if f == 1: return 'IF %s THEN %s ELSE %s -> %s / %s, hold %d' % (a[0], a[1], a[2], L(11), L(12), h)
    if f == 2: return 'VOTE >=%d of [%s] -> %s / %s, hold %d' % (int(row[9]), '; '.join(a), L(11), L(12), h)
    if f == 3: return 'LADDER [%s] both %s / one %s / none %s, hold %d' % ('; '.join(a), L(11), L(12), L(13), h)
    return 'VOTELADDER [%s] >=%d %s / >=%d %s / else %s, hold %d' % ('; '.join(a), int(row[9]), L(11), int(row[10]), L(12), L(13), h)


def setup():
    c = BM.Ctx()
    c.AM = json.load(open(SCR + 'cache/atoms_meta.json')); c.P = BM.pools(c.AM)
    E = MS.era_inputs(); c.names, X = products(E); c.nsl = len(c.names); P = NIDX + c.nsl
    c.CC = costc(P)
    A = {e: np.load(SCR + 'cache/atoms_%s.npy' % e, mmap_mode='r') for e in ('spx', 'ndx')}
    s0 = int(E['spx']['dates'].searchsorted(pd.Timestamp(SPX_START)))
    dsp = E['spx']['dates'][s0:]
    ms, ws0, ws1 = MS.month_slots(dsp, *DISC['spx'], 0); nspx = int(ms.max()) + 1
    mn, wn0, wn1 = MS.month_slots(E['ndx']['dates'], *DISC['ndx'], nspx); nmon = int(mn.max()) + 1
    c.nmon = nmon; c.nspx = nspx; c.s0 = s0
    c.spx = (np.ascontiguousarray(A['spx'][:, s0:s0 + ws1]), BM.logx(np.ascontiguousarray(X['spx'][:, s0:s0 + ws1])), ws1, ms, ws0, ws1)
    c.ndx = (np.ascontiguousarray(A['ndx'][:, :wn1]), BM.logx(np.ascontiguousarray(X['ndx'][:, :wn1])), wn1, mn, wn0, wn1)
    c.W = ST.stationary_counts(nmon)
    c.HM = np.random.default_rng(7).integers(1, 2**62, size=nmon, dtype=np.uint64) | np.uint64(1)
    c.X = X; c.E = E
    return c


def screen_chunk(c, rr):
    n = len(rr); om = np.zeros((n, c.nmon), np.float32); os_ = np.zeros((n, 4)); os2 = np.zeros((n, 4))
    A, LX, t1, mon, w0, w1 = c.spx
    BM.screen(A, LX, rr, t1, mon, c.nmon, w0, w1, c.CC, om, os_)
    A, LX, t1, mon, w0, w1 = c.ndx
    BM.screen(A, LX, rr, t1, mon, c.nmon, w0, w1, c.CC, om, os2)
    return om, np.hstack([os_, os2])


def run_shard(c, shard, n=BM.SHARD, outdir=None):
    """identical reduction to bt1_mega.run_shard (copied call sequence), with SL1 generator / products / windows."""
    outdir = outdir or SCR + 'out/sl1_shards/'
    BM_gen, BM_scr = BM.gen_shard, BM.screen_chunk
    try:
        BM.gen_shard = lambda AM, s, nn, P: gen_shard(AM, s, nn, P, c.nsl)
        BM.screen_chunk = screen_chunk
        BM.run_shard(c, shard, n, outdir)
    finally:
        BM.gen_shard, BM.screen_chunk = BM_gen, BM_scr


if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else BM.SHARD
    od = sys.argv[4] if len(sys.argv) > 4 else None
    c = setup()
    for s in range(a, b):
        run_shard(c, s, n, od)
