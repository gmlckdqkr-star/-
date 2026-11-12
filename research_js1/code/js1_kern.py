"""JS1 kernel: exposure-neutral pooled z for rules over annual country-year atoms (numba, bit-parallel). See PRECOMMIT_JS1.md."""
import numpy as np, os, threading
from numba import njit
M1 = np.uint64(0x5555555555555555); M2 = np.uint64(0x3333333333333333); M4 = np.uint64(0x0F0F0F0F0F0F0F0F); H01 = np.uint64(0x0101010101010101)
COST = np.array([0.006, 0.003, 0.003])          # per ON/OFF switch: 3x<->1x two ETF trades; 3x<->cash; 1x<->cash
KTOP = 2000; NCNT = 5; THR = np.array([3.5, 4.0, 4.5, 5.0, 5.5])

@njit(inline='always')
def pc(x):
    x = x - ((x >> np.uint64(1)) & M1); x = (x & M2) + ((x >> np.uint64(2)) & M2); x = (x + (x >> np.uint64(4))) & M4
    return (x * H01) >> np.uint64(56)

def prep(P, pre):
    """arrays for the kernel from a packed obs set (pre = 'des' or 'con')."""
    bits = np.ascontiguousarray(P[pre + '_bits']); A, NB = bits.shape; W = NB // 8
    b64 = np.ascontiguousarray(bits).view(np.uint64).reshape(A, W)
    xd = P[pre + '_xd']; valid = P[pre + '_valid']; first = P[pre + '_first']
    T = np.zeros((3, NB, 256)); vb = (np.arange(256)[:, None] >> np.arange(8)) & 1           # (256,8)
    for m in range(3): T[m] = xd[m].reshape(NB, 8) @ vb.T
    nfbits = (valid & ~first).reshape(NB, 8); nf = np.packbits(nfbits, axis=1, bitorder='little').reshape(NB)
    nf64 = np.ascontiguousarray(nf).view(np.uint64)
    ur = P[pre + '_unit_rng'].astype(np.int64); wu = P[pre + '_wu']; nu = P[pre + '_n_u'].astype(np.float64)
    return b64, T, nf64, ur, wu, nu, int(valid.sum())

@njit(inline='always')
def eval_rule(b64, T, nf64, ur, wu, nu, ntot, shape, a, b, c, d, z):
    W = b64.shape[1]; U = ur.shape[0]
    on = np.empty(W, np.uint64)
    for w in range(W):
        A = b64[a, w]; B = b64[b, w] if shape > 0 else A; C = b64[c, w]; D = b64[d, w]
        if shape == 0: v = A
        elif shape == 1: v = A & B
        elif shape == 2: v = A | B
        elif shape == 3: v = A & B & C
        elif shape == 4: v = A | B | C
        elif shape == 5: v = A & (B | C)
        elif shape == 6: v = B & (A | C)
        elif shape == 7: v = C & (A | B)
        elif shape == 8: v = A | (B & C)
        elif shape == 9: v = B | (A & C)
        elif shape == 10: v = C | (A & B)
        elif shape == 11: v = A & B & C & D
        elif shape == 12: v = (A & B) | (C & D)
        elif shape == 13: v = A & B & (C | D)
        elif shape == 14: v = A & (B | C | D)
        elif shape == 15: v = A | B | C | D
        else: v = (A | B) & (C | D)
        on[w] = v
    n_on = 0
    for w in range(W): n_on += np.int64(pc(on[w]))
    if n_on < 30 or ntot - n_on < 30 or 2 * n_on < ntot: return False
    flips = 0; carry = np.uint64(0)
    for w in range(W):
        sh = (on[w] << np.uint64(1)) | carry; carry = on[w] >> np.uint64(63)
        flips += np.int64(pc((on[w] ^ sh) & nf64[w]))
    var0 = 0.0; var1 = 0.0; var2 = 0.0
    for u in range(U):
        k = 0
        for w in range(ur[u, 0], ur[u, 1]): k += np.int64(pc(on[w]))
        p = k / nu[u]; q = p * (1 - p)
        var0 += q * wu[0, u]; var1 += q * wu[1, u]; var2 += q * wu[2, u]
    s0 = 0.0; s1 = 0.0; s2 = 0.0
    for w in range(W):
        x = on[w]
        for j in range(8):
            by = np.int64((x >> np.uint64(8 * j)) & np.uint64(255)); i = w * 8 + j
            s0 += T[0, i, by]; s1 += T[1, i, by]; s2 += T[2, i, by]
    z[0] = (s0 - 0.006 * flips) / np.sqrt(var0) if var0 > 0 else 0.0
    z[1] = (s1 - 0.003 * flips) / np.sqrt(var1) if var1 > 0 else 0.0
    z[2] = (s2 - 0.003 * flips) / np.sqrt(var2) if var2 > 0 else 0.0
    return True

@njit(inline='always')
def code_of(shape, a, b, c, d): return np.uint64(shape) | (np.uint64(a) << np.uint64(5)) | (np.uint64(b) << np.uint64(16)) | (np.uint64(c) << np.uint64(27)) | (np.uint64(d) << np.uint64(38))

@njit(inline='always')
def record(z, code, topz, topc, topmin, cnt, mx):
    for m in range(3):
        v = z[m]
        for t in range(5):
            if v >= THR[t]: cnt[m, t] += 1
        if v > mx[m]: mx[m] = v
        if v > topz[m, topmin[m]]:
            topz[m, topmin[m]] = v; topc[m, topmin[m]] = code
            j = 0; best = topz[m, 0]
            for i in range(1, topz.shape[1]):
                if topz[m, i] < best: best = topz[m, i]; j = i
            topmin[m] = j

@njit(nogil=True)
def enum_worker(b64, T, nf64, ur, wu, nu, ntot, nA, tid, nth, mode, topz, topc, cnt, mx, ndone):
    """mode 1: all singles/pairs/triples (a-loop interleaved over threads). z buffer local."""
    z = np.zeros(3); topmin = np.zeros(3, np.int64)
    for a in range(tid, nA, nth):
        if eval_rule(b64, T, nf64, ur, wu, nu, ntot, 0, a, a, a, a, z): record(z, code_of(0, a, 0, 0, 0), topz, topc, topmin, cnt, mx)
        ndone[0] += 1
        for b in range(a + 1, nA):
            for sh in range(1, 3):
                if eval_rule(b64, T, nf64, ur, wu, nu, ntot, sh, a, b, b, b, z): record(z, code_of(sh, a, b, 0, 0), topz, topc, topmin, cnt, mx)
            ndone[0] += 2
            for c in range(b + 1, nA):
                for sh in range(3, 11):
                    if eval_rule(b64, T, nf64, ur, wu, nu, ntot, sh, a, b, c, c, z): record(z, code_of(sh, a, b, c, 0), topz, topc, topmin, cnt, mx)
                ndone[0] += 8

@njit(inline='always')
def xs_next(s):
    s ^= s << np.uint64(13); s ^= s >> np.uint64(7); s ^= s << np.uint64(17); return s

@njit(nogil=True)
def rand_worker(b64, T, nf64, ur, wu, nu, ntot, nA, N, seed, topz, topc, cnt, mx, ndone):
    """N random rules: sizes 2/3/4 = 10/40/50%, shape uniform within size, distinct atoms; same (seed) => same rule set for every table T."""
    z = np.zeros(3); topmin = np.zeros(3, np.int64); s = np.uint64(seed) * np.uint64(0x9E3779B97F4A7C15) + np.uint64(88172645463325252)
    for _ in range(100): s = xs_next(s)
    for it in range(N):
        s = xs_next(s); u = (s >> np.uint64(11)) % np.uint64(100)
        if u < 10: k = 2
        elif u < 50: k = 3
        else: k = 4
        ids = np.zeros(4, np.int64)
        for i in range(k):
            while True:
                s = xs_next(s); v = np.int64((s >> np.uint64(11)) % np.uint64(nA)); ok = True
                for j in range(i):
                    if ids[j] == v: ok = False
                if ok: break
            ids[i] = v
        s = xs_next(s); r = np.int64((s >> np.uint64(11)) % np.uint64(1000))
        if k == 2: sh = 1 + r % 2
        elif k == 3: sh = 3 + r % 8
        else: sh = 11 + r % 6
        if eval_rule(b64, T, nf64, ur, wu, nu, ntot, sh, ids[0], ids[1], ids[2], ids[3], z): record(z, code_of(sh, ids[0], ids[1], ids[2], ids[3]), topz, topc, topmin, cnt, mx)
        ndone[0] += 1

def run_threads(fn, nth, *args_per_thread):
    outs = [None] * nth
    def w(i): outs[i] = fn(i)
    ts = [threading.Thread(target=w, args=(i,)) for i in range(nth)]
    for t in ts: t.start()
    for t in ts: t.join()
    return outs
