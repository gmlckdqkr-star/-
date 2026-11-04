"""KL1 locked generator (PRECOMMIT_KL1.md sec.6). Seed 20261141, numpy default_rng via SeedSequence spawn (one child per
family, fixed order). Written before any KL1 performance number. Output: integer rows per family.
S1 row : [form(0 single,1 comp,2 vote,3 regime-single,4 regime-comp), nd, d1, d2, d3, d4, k, qi, hi, fi, ra, rw]
S2 row : [a1, a2, a3, struct, pon_code, poff_code, hold]  (M1 format; codes 0=3x 1=2x 2=1x 3=cash 4=-1x)
S3 row : [form(0 single,1 comp2), d1, d2, qi, hi, wi, prod, ov_atom(-1 none), offmode]"""
import numpy as np

SEED = 20261141
Q1 = (0.05, 0.10, 0.20, 0.30)
Q3 = (0.10, 0.20, 0.30)
HS = (5, 21, 63)
HOLDS = (1, 5, 21)
W_KR = (0.5, 0.67, 0.8)
W_US = (0.25, 0.33, 0.5)
# shapes (on, off) -> product codes
SH_KR = ((1, 3), (1, 2), (1, 4), (2, 3), (2, 4), (3, 4))                      # (2,0) (2,1) (2,-1) (1,0) (1,-1) (0,-1)
SH_US = ((0, 3), (0, 2), (1, 3), (2, 3), (0, 4), (1, 4), (2, 4))              # M1 SHAPES
N_S1_RAND = {'KR': 30000, 'US': 15000}
N_PAIRS, N_TRIPLES = 150000, 50000
N_S3 = 20000
NCORE = 12


def _children():
    ss = np.random.SeedSequence(SEED)
    return dict(zip(['S1KR', 'S1US', 'S2KR', 'S2US', 'S3KR', 'S3US'], [np.random.default_rng(c) for c in ss.spawn(6)]))


def _draw_defs(rng, n, ndefs_total, kr):
    """n distinct definition indices; KR: each slot from KR-only (indices 12..20) with prob 1/3, else core 0..11."""
    out = []
    while len(out) < n:
        if kr and rng.random() < 1 / 3:
            d = int(rng.integers(NCORE, ndefs_total))
        else:
            d = int(rng.integers(0, NCORE))
        if d not in out:
            out.append(d)
    return out


def gen_s1(panel, ndefs, n_atoms, rng):
    kr = panel == 'KR'
    rows = []
    nf = 3 if kr else 1
    for d in range(ndefs):                       # singles, full enumeration
        for qi in range(len(Q1)):
            for hi in range(len(HS)):
                for fi in range(nf):
                    rows.append([0, 1, d, -1, -1, -1, 0, qi, hi, fi, -1, 0])
    for _ in range(N_S1_RAND[panel]):
        form = int(rng.integers(0, 3))           # 0 comp, 1 vote, 2 regime
        qi = int(rng.integers(0, len(Q1))); hi = int(rng.integers(0, len(HS))); fi = int(rng.integers(0, nf))
        if form == 0:
            m = int(rng.integers(2, 4)); ds = _draw_defs(rng, m, ndefs, kr)
            rows.append([1, m] + ds + [-1] * (4 - m) + [0, qi, hi, fi, -1, 0])
        elif form == 1:
            m = int(rng.integers(2, 5)); k = int(rng.integers(1, m + 1)); ds = _draw_defs(rng, m, ndefs, kr)
            rows.append([2, m] + ds + [-1] * (4 - m) + [k, qi, hi, fi, -1, 0])
        else:
            a = int(rng.integers(0, n_atoms)); want = int(rng.integers(0, 2))
            if rng.random() < 0.5:
                d = int(rng.integers(0, ndefs)); rows.append([3, 1, d, -1, -1, -1, 0, qi, hi, fi, a, want])
            else:
                m = int(rng.integers(2, 4)); ds = _draw_defs(rng, m, ndefs, kr)
                rows.append([4, m] + ds + [-1] * (4 - m) + [0, qi, hi, fi, a, want])
    return np.array(rows, np.int64)


def gen_s2(panel, atom_feat, rng):
    """atom_feat: int array [n_atoms] feature id of each atom."""
    shapes = SH_KR if panel == 'KR' else SH_US
    n = len(atom_feat)
    rows = []
    for a in range(n):
        for s in shapes:
            for h in HOLDS:
                rows.append([a, 0, 0, 0, s[0], s[1], h])
    def distinct(k):
        while True:
            aa = rng.integers(0, n, k)
            if len(set(atom_feat[aa].tolist())) == k:
                return [int(x) for x in aa]
    for _ in range(N_PAIRS):
        a1, a2 = distinct(2); st = 1 if rng.random() < 0.5 else 2
        s = shapes[int(rng.integers(0, len(shapes)))]; h = HOLDS[int(rng.integers(0, 3))]
        rows.append([a1, a2, 0, st, s[0], s[1], h])
    for _ in range(N_TRIPLES):
        a1, a2, a3 = distinct(3); st = int(rng.integers(3, 7))
        s = shapes[int(rng.integers(0, len(shapes)))]; h = HOLDS[int(rng.integers(0, 3))]
        rows.append([a1, a2, a3, st, s[0], s[1], h])
    return np.array(rows, np.int64)


def gen_s3(panel, n_atoms, rng):
    rows = []
    for _ in range(N_S3):
        if rng.random() < 0.5:
            form = 0; d1 = int(rng.integers(0, NCORE)); d2 = -1
        else:
            form = 1; d1, d2 = [int(x) for x in rng.choice(NCORE, 2, replace=False)]
        qi = int(rng.integers(0, len(Q3))); hi = int(rng.integers(0, len(HS))); wi = int(rng.integers(0, 3))
        prod = int(rng.integers(0, 2)) if panel == 'US' else 0
        if rng.random() < 0.6:
            ov = int(rng.integers(0, n_atoms)); om = int(rng.integers(0, 4))
        else:
            ov = -1; om = 0
        rows.append([form, d1, d2, qi, hi, wi, prod, ov, om])
    return np.array(rows, np.int64)


def generate_all(n_defs, atom_feat):
    """n_defs: {'KR': 21, 'US': 12}; atom_feat: {'KR': array, 'US': array}. Fixed order of draws."""
    ch = _children()
    out = {}
    out['S1KR'] = gen_s1('KR', n_defs['KR'], len(atom_feat['KR']), ch['S1KR'])
    out['S1US'] = gen_s1('US', n_defs['US'], len(atom_feat['US']), ch['S1US'])
    out['S2KR'] = gen_s2('KR', atom_feat['KR'], ch['S2KR'])
    out['S2US'] = gen_s2('US', atom_feat['US'], ch['S2US'])
    out['S3KR'] = gen_s3('KR', len(atom_feat['KR']), ch['S3KR'])
    out['S3US'] = gen_s3('US', len(atom_feat['US']), ch['S3US'])
    return out
