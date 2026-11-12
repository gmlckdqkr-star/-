"""MX2 helpers: tables, placebo shifts, kernel I/O, numpy reference evaluator, walk-forward selection."""
import numpy as np, struct, subprocess, os
R = '/mnt/project-files/research/mx2/'
Z = np.load(R + 'data/mx2.npz')
A8, BITS, NAMES, YR, SEG = Z['A8'], Z['bits'], Z['names'], Z['yr'], Z['seg']
D0, CB0 = Z['D'], Z['CB']
NH, NY, C0 = 120, 60, 11
YEARS = np.arange(1955, 2015)

def shift_DC(D, CB, s_spx, s_ndx):
    D = D.copy(); CB = CB.copy()
    for (lo, hi), s in (((0, 372), s_spx), ((372, 720), s_ndx)):
        D[:, lo:hi] = np.roll(D[:, lo:hi], s, axis=1); CB[:, lo:hi] = np.roll(CB[:, lo:hi], s, axis=1)
    return D, CB

def tables(D, CB):
    T = np.zeros((4, NH, 128), np.float32)
    pat = np.arange(128); p = (pat[:, None] >> np.arange(6)) & 1; prev = (pat >> 6) & 1
    pp = np.concatenate([prev[:, None], p], 1)           # 128 x 7
    flip = (pp[:, 1:] != pp[:, :-1]).astype(float)       # 128 x 6
    for h in range(NH):
        m = slice(6 * h, 6 * h + 6)
        T[:, h, :] = (p @ D[:, m].T).T - (flip @ CB[:, m].T).T
    return T

def write_in(path, T):
    with open(path, 'wb') as f:
        f.write(struct.pack('i', A8.shape[0])); f.write(np.ascontiguousarray(A8).tobytes()); f.write(np.ascontiguousarray(T, np.float32).tobytes())

def run_kernel(T, mode, N, seed, tag, threads=4):
    inp = '/tmp/claude-0/mx2_%s.in' % tag; out = R + 'results/raw_%s.bin' % tag
    write_in(inp, T)
    env = dict(os.environ, OMP_NUM_THREADS=str(threads))
    p = subprocess.run(['/tmp/claude-0/mx2w/mx2', inp, out, str(mode), str(N), str(seed)], env=env, capture_output=True, text=True)
    os.remove(inp)
    return out, p.stderr.strip()

def read_out(path):
    b = open(path, 'rb').read(); nt, NC, K, ns = struct.unpack('4i', b[:16]); ne = struct.unpack('Q', b[16:24])[0]
    arr = np.frombuffer(b[24:], dtype=np.uint8)
    S = np.zeros((nt, NC, ns, K)); C = np.zeros((nt, NC, ns, K), np.uint64); o = 0
    for t in range(nt):
        for c in range(NC):
            for s in range(ns):
                S[t, c, s] = np.frombuffer(b[24 + o:24 + o + 8 * K], '<f8'); o += 8 * K
                C[t, c, s] = np.frombuffer(b[24 + o:24 + o + 8 * K], '<u8'); o += 8 * K
    return S, C, ne

def decode(code):
    code = int(code)
    return code & 31, (code >> 5) & 2047, (code >> 16) & 2047, (code >> 27) & 2047, (code >> 38) & 2047, code >> 62

def cond_bits(code):
    sh, a, b, c, d, _ = decode(code); x = BITS
    A, B_, C_, D_ = x[a], x[b], x[c], x[d]
    return {0: A, 1: A & B_, 2: A | B_, 3: A & B_ & C_, 4: A & (B_ | C_), 5: B_ & (A | C_), 6: C_ & (A | B_), 7: A | (B_ & C_),
            8: B_ | (A & C_), 9: C_ | (A & B_), 10: A | B_ | C_, 11: A & B_ & C_ & D_, 12: (A & B_) | (C_ & D_),
            13: A & B_ & (C_ | D_), 14: A & (B_ | C_ | D_), 15: A | B_ | C_ | D_, 16: (A | B_) & (C_ | D_)}[sh]

def yearly_S(cond, act, D, CB):
    """exact (same model as kernel) yearly sums for one rule and action."""
    p = cond.astype(float); prev = np.r_[0, p[:-1]]
    m = p * D[act] - (p != prev) * CB[act]
    return np.array([m[12 * y:12 * y + 12].sum() for y in range(NY)])

def rule_name(code):
    sh, a, b, c, d, act = decode(code)
    n = {0: '{a}', 1: '{a} & {b}', 2: '{a} | {b}', 3: '{a} & {b} & {c}', 4: '{a} & ({b} | {c})', 5: '{b} & ({a} | {c})', 6: '{c} & ({a} | {b})',
         7: '{a} | ({b} & {c})', 8: '{b} | ({a} & {c})', 9: '{c} | ({a} & {b})', 10: '{a} | {b} | {c}', 11: '{a} & {b} & {c} & {d}',
         12: '({a} & {b}) | ({c} & {d})', 13: '{a} & {b} & ({c} | {d})', 14: '{a} & ({b} | {c} | {d})', 15: '{a} | {b} | {c} | {d}',
         16: '({a} | {b}) & ({c} | {d})'}[sh]
    return ['CUT1', 'CUT0', 'ADD3', 'ADD1'][act] + ': ' + n.format(a=NAMES[a], b=NAMES[b], c=NAMES[c], d=NAMES[d])

def select(S, C, st=0, topn=20, merge=None):
    """per cutoff: merge thread heaps (and optional extra result sets), dedupe by (score, action), take top-n codes."""
    out = []
    NC = S.shape[1]
    for c in range(NC):
        sc = [S[:, c, st].ravel()]; cd = [C[:, c, st].ravel()]
        if merge is not None:
            for (S2, C2) in merge: sc.append(S2[:, c, st].ravel()); cd.append(C2[:, c, st].ravel())
        sc = np.concatenate(sc); cd = np.concatenate(cd)
        o = np.argsort(-sc); seen = set(); sel = []
        for i in o:
            if sc[i] <= -1e299: break
            key = (round(float(sc[i]), 12), int(cd[i]) >> 62)
            if key in seen: continue
            seen.add(key); sel.append((float(sc[i]), int(cd[i])))
            if len(sel) == topn: break
        out.append(sel)
    return out

def wf_oos(sel, D, CB):
    """walk-forward OOS yearly delta (linear model): test year = C0 + c, ensemble = mean of selected rules' S in that year."""
    res = np.zeros(len(sel))
    for c, lst in enumerate(sel):
        y = C0 + c
        if not lst: continue
        res[c] = np.mean([yearly_S(cond_bits(cd), cd >> 62, D, CB)[y] for _, cd in lst])
    return res
