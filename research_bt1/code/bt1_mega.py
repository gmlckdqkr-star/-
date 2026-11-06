"""BT1 mega search (ADDENDUM_BT1_1): hundreds of millions of rules over 5 rule FORMS, streamed in shards.
Same discovery windows, products, costs, delay and stats definitions as M1 (m1_engine / m1_search / m1_stats):
discovery = real S&P 1955-01..1985-12 (own index S&P TR) + real NDX 1986-01..1999-12. No 2000+ number is computed here.
Per shard: rules are generated from rng([SEED, shard]); every rule is screened; per-rule monthly differential streams
are reduced on the fly to (a) SPA consistent/lower/upper bootstrap maxima per replicate, (b) per-replicate top-600
for Romano-Wolf, (c) Li-Ji Gram matrix, (d) Sharpe moments for DSR, (e) 64-bit stream hashes for the unique count,
(f) the best candidates by active-day advantage and by t (kept with their streams).
Rule row (int32, 15 cols): form, a0..a6, k, m1, m2, c1, c2, c3, hold. Product codes 0=3x 1=2x 2=1x 3=cash 4=-1x.
 form 0 BOOL     : struct k (0 single,1 AND,2 OR,3 AND3,4 OR3,5 (a&b)|c,6 (a|b)&c) -> c1 / c2
 form 1 SWITCH   : regime a0: v = a1 if a0 else a2 -> c1 / c2
 form 2 VOTE     : count of k atoms true >= m1 -> c1 / c2
 form 3 LADDER   : a0&a1 -> c1, exactly one -> c2, none -> c3
 form 4 VOTELAD  : count >= m1 -> c1, >= m2 -> c2, else c3
any used atom unknown -> rule inactive -> 1x (benchmark). Min-hold as M1 (state change needs age+1 >= hold)."""
import os, sys, json, time, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m1_data as DT
SCR = DT.SCR
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
from numba import njit, prange
import m1_engine as EN, m1_stats as ST, m1_search as MS

SEED = 20261105
SHARD = 2_000_000
CH = 20000
TOPM = 50
KEEP = 2000
NC = 15
SHAPES2 = EN.SHAPE_CODES                      # 7 (on, off)
LADDERS = np.array([[0, 2, 3], [0, 1, 2], [1, 2, 3], [0, 2, 4], [0, 3, 4], [2, 3, 4], [0, 1, 3]], np.int64)
HOLDS = np.array([1, 5, 21], np.int64)
COSTC = np.array([[np.log1p(-EN.COST * (EN.NONCASH[a] + EN.NONCASH[b])) if a != b else 0.0 for b in range(5)] for a in range(5)])


@njit(cache=True)
def rcode(A, r, t):
    """product code of rule row r at day t, or -1 if inactive."""
    f = r[0]
    if f == 0:
        st = r[8]
        v1 = A[r[1], t]
        if v1 < 0: return -1
        if st == 0:
            v = v1
        else:
            v2 = A[r[2], t]
            if v2 < 0: return -1
            if st == 1: v = 1 if (v1 == 1 and v2 == 1) else 0
            elif st == 2: v = 1 if (v1 == 1 or v2 == 1) else 0
            else:
                v3 = A[r[3], t]
                if v3 < 0: return -1
                if st == 3: v = 1 if (v1 == 1 and v2 == 1 and v3 == 1) else 0
                elif st == 4: v = 1 if (v1 == 1 or v2 == 1 or v3 == 1) else 0
                elif st == 5: v = 1 if ((v1 == 1 and v2 == 1) or v3 == 1) else 0
                else: v = 1 if ((v1 == 1 or v2 == 1) and v3 == 1) else 0
        return r[11] if v == 1 else r[12]
    if f == 1:
        g = A[r[1], t]; x = A[r[2], t]; y = A[r[3], t]
        if g < 0 or x < 0 or y < 0: return -1
        v = x if g == 1 else y
        return r[11] if v == 1 else r[12]
    if f == 3:
        x = A[r[1], t]; y = A[r[2], t]
        if x < 0 or y < 0: return -1
        c = x + y
        return r[11] if c == 2 else (r[12] if c == 1 else r[13])
    # vote forms
    k = r[8]; c = 0
    for j in range(k):
        v = A[r[1 + j], t]
        if v < 0: return -1
        c += v
    if f == 2:
        return r[11] if c >= r[9] else r[12]
    return r[11] if c >= r[9] else (r[12] if c >= r[10] else r[13])


@njit(parallel=True, cache=True)
def screen(A, LX, rules, t1, mon, nmon, w0, w1, CC, out_m, out_s):
    """out_m (n, nmon) += monthly sums of g in [w0, w1); out_s (n, 4): sum g, active days, switches, days."""
    N = rules.shape[0]
    for k in prange(N):
        r = rules[k]; hold = r[14]
        held = 2; age = 1 << 30; prev = 0
        d1 = 2; d2 = 2; d3 = 2                         # decisions of close t-1, t-2, t-3
        a1 = 0; a2 = 0; a3 = 0
        s = 0.0; na = 0.0; sw = 0.0
        for t in range(t1):
            v = rcode(A, r, t)
            if v < 0:
                act = 0
                if held != 2:
                    held = 2; age = 0
                else:
                    age += 1
                prev = 0
            else:
                act = 1
                if v != held:
                    if prev == 0 or age + 1 >= hold:
                        held = v; age = 0
                    else:
                        age += 1
                else:
                    age += 1
                prev = 1
            # shift: day t position = decision of close t-3; next-day position = decision of close t-2
            dt = held
            p = d3 if t >= 3 else 2
            pn = d2 if t >= 2 else 2
            lg = LX[p, t]
            if t + 1 < t1 and pn != p:
                lg += CC[p, pn]
            if t >= w0 and t < w1:
                m = mon[t]
                if m >= 0:
                    out_m[k, m] += lg
                s += lg
                if t >= 3 and a3 == 1:
                    na += 1
                if dt != d1:
                    sw += 1
            d3 = d2; d2 = d1; d1 = dt
            a3 = a2; a2 = a1; a1 = act
        out_s[k, 0] += s; out_s[k, 1] += na; out_s[k, 2] += sw; out_s[k, 3] += w1 - w0


@njit(parallel=True, cache=True)
def stats_kernel(Mt, dbar, T, nblk):
    """Mt (n, B) bootstrap means per rule. Returns om (n), colmax (n), per-replicate maxima Tu/Tc/Tl (B) of the
    centered studentized statistic (upper / consistent / lower SPA recentering, Hansen 2005, as m1_stats)."""
    n, B = Mt.shape
    om = np.zeros(n); colmax = np.full(n, -np.inf)
    pu = np.full((nblk, B), -np.inf); pc = np.full((nblk, B), -np.inf); pl = np.full((nblk, B), -np.inf)
    sT = np.sqrt(T); ll = np.sqrt(2 * np.log(np.log(T)))
    for blk in prange(nblk):
        j0 = blk * n // nblk; j1 = (blk + 1) * n // nblk
        for j in range(j0, j1):
            m = 0.0
            for b in range(B): m += Mt[j, b]
            m /= B; v = 0.0
            for b in range(B):
                d = Mt[j, b] - m; v += d * d
            v /= B
            o = np.sqrt(max(v, 0.0) * T)
            if o <= 1e-10:
                continue
            om[j] = o; sc = sT / o; db = dbar[j]
            A = -(o / sT) * ll
            gc = db if db >= A else 0.0
            gl = db if db > 0 else 0.0
            offc = (db - gc) * sc; offl = (db - gl) * sc
            cm = -np.inf
            for b in range(B):
                z = (Mt[j, b] - db) * sc
                if z > cm: cm = z
                if z > pu[blk, b]: pu[blk, b] = z
                if z + offc > pc[blk, b]: pc[blk, b] = z + offc
                if z + offl > pl[blk, b]: pl[blk, b] = z + offl
            colmax[j] = cm
    Tu = np.full(B, -np.inf); Tc = np.full(B, -np.inf); Tl = np.full(B, -np.inf)
    for blk in range(nblk):
        for b in range(B):
            if pu[blk, b] > Tu[b]: Tu[b] = pu[blk, b]
            if pc[blk, b] > Tc[b]: Tc[b] = pc[blk, b]
            if pl[blk, b] > Tl[b]: Tl[b] = pl[blk, b]
    return om, colmax, Tu, Tc, Tl


@njit(parallel=True, cache=True)
def row_kernel(D, HM, Z):
    """per rule: 64-bit stream hash, Sharpe over months from the first non-zero month (nan if <= 24 months or flat),
    standardized row (into Z, zero if constant)."""
    n, T = D.shape
    H = np.zeros(n, np.uint64); SR = np.full(n, np.nan)
    for j in prange(n):
        h = np.uint64(0); fm = T
        for t in range(T):
            x = D[j, t]
            h += np.uint64(np.int64(np.float32(x).view(np.int32)) & 0xFFFFFFFF) * HM[t]
            if fm == T and x != 0: fm = t
        H[j] = h
        c = T - fm
        if c > 24:
            m = 0.0
            for t in range(fm, T): m += D[j, t]
            m /= c; v = 0.0
            for t in range(fm, T):
                d = D[j, t] - m; v += d * d
            v /= (c - 1)
            if v > 0: SR[j] = m / np.sqrt(v)
        m = 0.0
        for t in range(T): m += D[j, t]
        m /= T; ss = 0.0
        for t in range(T):
            d = D[j, t] - m; ss += d * d
        sd = np.sqrt(ss)
        for t in range(T):
            Z[j, t] = (D[j, t] - m) / sd if sd > 0 else 0.0
    return H, SR


def logx(X):
    L = np.log1p(X)
    return np.ascontiguousarray(L - L[2][None, :])


def pools(AM):
    def key(m): return (m['prim'], m['tr']) if m['prim'] in ('macro', 'c3sig') else (m['prim'],)
    kid = {}
    K = np.array([kid.setdefault(key(m), len(kid)) for m in AM], np.int64)
    new = np.array([i for i, m in enumerate(AM) if m.get('new')], np.int64)
    old = np.array([i for i, m in enumerate(AM) if not m['c3'] and not m.get('new')], np.int64)
    c3s = np.array([i for i, m in enumerate(AM) if m['prim'] == 'c3sig'], np.int64)
    mac = np.array([i for i, m in enumerate(AM) if m['prim'] == 'macro'], np.int64)
    oth = np.array([i for i, m in enumerate(AM) if m['c3'] and m['prim'] not in ('macro', 'c3sig')], np.int64)
    return K, new, old, c3s, mac, oth


def gen_shard(AM, shard, n, P=None):
    """rules of one shard (deterministic). Shard 0 begins with every new-atom single x 7 shapes x 3 holds."""
    K, new, old, c3s, mac, oth = P if P is not None else pools(AM)
    isnew = np.zeros(len(AM), bool); isnew[new] = True
    isc3 = np.array([m['c3'] for m in AM])
    rng = np.random.default_rng([SEED, shard])
    R = np.full((n, NC), -1, np.int32); i = 0
    if shard == 0:
        for a in new:
            for s in range(7):
                for h in HOLDS:
                    R[i, :] = -1; R[i, 0] = 0; R[i, 1] = a; R[i, 8] = 0; R[i, 9] = 0; R[i, 10] = 0
                    R[i, 11] = SHAPES2[s, 0]; R[i, 12] = SHAPES2[s, 1]; R[i, 13] = 0; R[i, 14] = h; i += 1
    B = 200000
    while i < n:
        m = min(B, (n - i) * 3)
        form = rng.choice(5, size=m, p=[0.30, 0.15, 0.20, 0.15, 0.20])
        nat = np.where(form == 0, rng.integers(2, 4, size=m), np.where(form == 1, 3, np.where(form == 3, 2, rng.choice([3, 5, 7], size=m))))
        u = rng.random((m, 7)); pick = np.empty((m, 7), np.int64)
        cu = rng.random((m, 7))
        pn = new[rng.integers(len(new), size=(m, 7))]; po = old[rng.integers(len(old), size=(m, 7))]
        pc = np.where(cu < 0.25, c3s[rng.integers(len(c3s), size=(m, 7))], np.where(cu < 0.5, mac[rng.integers(len(mac), size=(m, 7))], oth[rng.integers(len(oth), size=(m, 7))]))
        pick = np.where(u < 0.45, pn, np.where(u < 0.75, po, pc))
        slot = np.arange(7)[None, :] < nat[:, None]
        ks = np.where(slot, K[pick], -np.arange(1, 8)[None, :])
        srt = np.sort(ks, 1); distinct = (np.diff(srt, axis=1) != 0).all(1)
        anyn = (isnew[pick] & slot).any(1); anynon3 = ((~isc3[pick]) & slot).any(1)
        ok = distinct & anynon3 & np.where(form == 0, anyn, True)
        st = np.where(nat == 2, rng.integers(1, 3, size=m), rng.integers(3, 7, size=m))
        sh = rng.integers(7, size=m); ld = rng.integers(len(LADDERS), size=m); hd = HOLDS[rng.integers(3, size=m)]
        m1 = np.array([rng.integers(1, k + 1) for k in nat]) if False else (np.floor(rng.random(m) * nat).astype(np.int64) + 1)
        # vote-ladder thresholds: m2 < m1, m1 in 2..k
        vm1 = np.floor(rng.random(m) * (nat - 1)).astype(np.int64) + 2
        vm2 = np.floor(rng.random(m) * (vm1 - 1)).astype(np.int64) + 1
        for j in np.flatnonzero(ok):
            if i >= n: break
            f = int(form[j]); k = int(nat[j]); row = np.full(NC, -1, np.int32); row[0] = f
            row[1:1 + k] = pick[j, :k]; row[14] = hd[j]
            if f == 0:
                row[8] = st[j]; row[11], row[12] = SHAPES2[sh[j]]
            elif f == 1:
                row[8] = 3; row[11], row[12] = SHAPES2[sh[j]]
            elif f == 2:
                row[8] = k; row[9] = m1[j]; row[11], row[12] = SHAPES2[sh[j]]
            elif f == 3:
                row[8] = 2; row[11], row[12], row[13] = LADDERS[ld[j]]
            else:
                row[8] = k; row[9] = vm1[j]; row[10] = vm2[j]; row[11], row[12], row[13] = LADDERS[ld[j]]
            R[i] = row; i += 1
    return R


def describe(AM, row):
    lev = {0: '3x', 1: '2x', 2: '1x', 3: 'cash', 4: '-1x'}
    def at(i):
        m = AM[i]; q = '' if m['q'] == 0 else '@q%.1f' % m['q']
        return '%s.%s%s%s' % (m['prim'], m['tr'], m['dir'], q)
    f = int(row[0]); a = [at(int(x)) for x in row[1:8] if x >= 0]; h = int(row[14])
    if f == 0:
        e = EN_desc(int(row[8]), a)
        return '%s -> %s / %s, hold %d' % (e, lev[int(row[11])], lev[int(row[12])], h)
    if f == 1:
        return 'IF %s THEN %s ELSE %s -> %s / %s, hold %d' % (a[0], a[1], a[2], lev[int(row[11])], lev[int(row[12])], h)
    if f == 2:
        return 'VOTE >=%d of [%s] -> %s / %s, hold %d' % (int(row[9]), '; '.join(a), lev[int(row[11])], lev[int(row[12])], h)
    if f == 3:
        return 'LADDER [%s] both %s / one %s / none %s, hold %d' % ('; '.join(a), lev[int(row[11])], lev[int(row[12])], lev[int(row[13])], h)
    return 'VOTELADDER [%s] >=%d %s / >=%d %s / else %s, hold %d' % ('; '.join(a), int(row[9]), lev[int(row[11])], int(row[10]), lev[int(row[12])], lev[int(row[13])], h)


def EN_desc(st, a):
    if st == 0: return a[0]
    if st == 1: return '(%s AND %s)' % (a[0], a[1])
    if st == 2: return '(%s OR %s)' % (a[0], a[1])
    if st == 3: return '(%s AND %s AND %s)' % tuple(a[:3])
    if st == 4: return '(%s OR %s OR %s)' % tuple(a[:3])
    if st == 5: return '((%s AND %s) OR %s)' % tuple(a[:3])
    return '((%s OR %s) AND %s)' % tuple(a[:3])


class Ctx:
    pass


def setup():
    c = Ctx()
    c.AM = json.load(open(SCR + 'cache/atoms_meta.json'))
    c.P = pools(c.AM)
    E = MS.era_inputs()
    A = {e: np.load(SCR + 'cache/atoms_%s.npy' % e, mmap_mode='r') for e in ('spx', 'ndx')}
    ms, ws0, ws1 = MS.month_slots(E['spx']['dates'], *MS.DISC['spx'], 0); nspx = int(ms.max()) + 1
    mn, wn0, wn1 = MS.month_slots(E['ndx']['dates'], *MS.DISC['ndx'], nspx); nmon = int(mn.max()) + 1
    c.nmon = nmon; c.nspx = nspx
    c.spx = (np.ascontiguousarray(A['spx'][:, :ws1]), logx(E['spx']['X'][:, :ws1]), ws1, ms, ws0, ws1)
    c.ndx = (np.ascontiguousarray(A['ndx'][:, :wn1]), logx(np.ascontiguousarray(E['ndx']['X'][:, :wn1])), wn1, mn, wn0, wn1)
    c.W = ST.stationary_counts(nmon)          # same bootstrap as M1 (seed 20261104, B 1000, mean block 3)
    c.HM = np.random.default_rng(7).integers(1, 2**62, size=nmon, dtype=np.uint64) | np.uint64(1)
    return c


def screen_chunk(c, rr):
    n = len(rr); om = np.zeros((n, c.nmon), np.float32); os_ = np.zeros((n, 4)); os2 = np.zeros((n, 4))
    A, LX, t1, mon, w0, w1 = c.spx
    screen(A, LX, rr, t1, mon, c.nmon, w0, w1, COSTC, om, os_)
    A, LX, t1, mon, w0, w1 = c.ndx
    screen(A, LX, rr, t1, mon, c.nmon, w0, w1, COSTC, om, os2)
    return om, np.hstack([os_, os2])


def run_shard(c, shard, n=SHARD, outdir=None):
    t0 = time.time()
    outdir = outdir or SCR + 'out/shards/'; os.makedirs(outdir, exist_ok=True)
    fn = outdir + 's%04d.npz' % shard
    if os.path.exists(fn): return
    R = gen_shard(c.AM, shard, n, c.P)
    T = c.nmon; B = c.W.shape[0]; W = c.W
    Tc = np.full(B, -np.inf); Tl = np.full(B, -np.inf); Tu = np.full(B, -np.inf)
    topv = np.full((B, TOPM), -np.inf, np.float32); topk = np.full((B, TOPM), -1, np.int64)
    G = np.zeros((T, T)); nG = 0
    tmax = -np.inf; srs = 0.0; srs2 = 0.0; srn = 0; nzero = 0; ngood = 0
    H = np.empty(n, np.uint64)
    cand = []   # (score arrays later)
    CA = dict(id=[], adv=[], t=[], dbar=[], om=[], row=[], D=[], S=[])
    base = shard * n
    for i in range(0, n, CH):
        rr = np.ascontiguousarray(R[i:i + CH]); D, S = screen_chunk(c, rr)
        Z = np.empty_like(D); h, SR = row_kernel(D, c.HM, Z); H[i:i + len(rr)] = h
        dbar = D.mean(1).astype(np.float64)
        Mt = np.ascontiguousarray((D @ W.T) / np.float32(T))                  # (n, B) bootstrap means
        om, colmax, tu, tc, tl = stats_kernel(Mt, dbar, T, 64)
        good = om > 1e-10
        nzero += int((~good).sum()); ngood += int(good.sum())
        oms = np.where(good, om, np.inf); ts = np.sqrt(T) * dbar / oms
        if good.any(): tmax = max(tmax, float(ts[good].max()))
        Tu = np.maximum(Tu, tu); Tc = np.maximum(Tc, tc); Tl = np.maximum(Tl, tl)
        # exact per-replicate top-TOPM merge with a column prefilter (ADDENDUM_BT1_1: RW stepdown)
        sc = np.where(good, np.sqrt(T) / np.where(good, om, 1.0), 0.0)
        nsub = min(int(good.sum()), 4 * TOPM)
        if nsub > 0:
            gi = np.flatnonzero(good)
            sub = gi[np.argpartition(-colmax[gi], nsub - 1)[:nsub]]
            Zs_ = ((Mt[sub] - dbar[sub, None]) * sc[sub, None]).T                # (B, nsub)
            kk = min(TOPM, nsub)
            thr_sub = -np.partition(-Zs_, kk - 1, axis=1)[:, kk - 1]
            thr = float(np.min(np.maximum(thr_sub, topv[:, -1])))
            cols = np.flatnonzero(good & (colmax >= thr))
            v = ((Mt[cols] - dbar[cols, None]) * sc[cols, None]).T.astype(np.float32)
            kcol = cols + base + i
            allv = np.concatenate([topv, v], 1); allk = np.concatenate([topk, np.broadcast_to(kcol, (B, len(cols)))], 1)
            o = np.argpartition(-allv, TOPM - 1, axis=1)[:, :TOPM]
            topv = np.take_along_axis(allv, o, 1); topk = np.take_along_axis(allk, o, 1)
            o = np.argsort(-topv, 1); topv = np.take_along_axis(topv, o, 1); topk = np.take_along_axis(topk, o, 1)
        Zg = Z[good]; G += (Zg.T @ Zg).astype(np.float64); nG += len(Zg)
        okk = good & np.isfinite(SR); srs += float(SR[okk].sum()); srs2 += float((SR[okk] ** 2).sum()); srn += int(okk.sum())
        act = S[:, 1] + S[:, 5]; adv = (S[:, 0] + S[:, 4]) / np.maximum(act, 1) * 252
        el = (act >= MS.MIN_ACTIVE) & good
        sel = set(np.flatnonzero(el)[np.argsort(-adv[el])][:200].tolist()) | set(np.flatnonzero(good)[np.argsort(-ts[good])][:200].tolist())
        for j in sel:
            CA['id'].append(base + i + j); CA['adv'].append(adv[j] if el[j] else -np.inf); CA['t'].append(ts[j])
            CA['dbar'].append(dbar[j]); CA['om'].append(om[j]); CA['row'].append(R[i + j]); CA['D'].append(D[j]); CA['S'].append(S[j])
    adv = np.array(CA['adv']); tt = np.array(CA['t'])
    keep = sorted(set(np.argsort(-adv)[:KEEP].tolist()) | set(np.argsort(-tt)[:KEEP].tolist()))
    np.savez(fn + '.tmp.npz', Tc=Tc, Tl=Tl, Tu=Tu, topv=topv, topk=topk, G=G, nG=nG, tmax=tmax, srs=srs, srs2=srs2, srn=srn,
             nzero=nzero, ngood=ngood, H=H, n=n, forms=np.bincount(R[:, 0], minlength=5),
             c_id=np.array(CA['id'])[keep], c_adv=adv[keep], c_t=tt[keep], c_dbar=np.array(CA['dbar'])[keep], c_om=np.array(CA['om'])[keep],
             c_row=np.array(CA['row'])[keep], c_D=np.array(CA['D'])[keep], c_S=np.array(CA['S'])[keep], secs=time.time() - t0)
    os.replace(fn + '.tmp.npz', fn)
    print('shard', shard, 'n', n, '%.0fs' % (time.time() - t0), time.strftime('%H:%M:%SZ', time.gmtime()), flush=True)


if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else SHARD
    od = sys.argv[4] if len(sys.argv) > 4 else None
    c = setup()
    for s in range(a, b):
        run_shard(c, s, n, od)
