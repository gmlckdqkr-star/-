"""M1 rule generator (locked before any search result; seed 20261104).
Rule row = [a1, a2, a3, struct, on_code, off_code, hold]; struct 0 single, 1 AND, 2 OR, 3 AND3, 4 OR3, 5 (a1&a2)|a3,
6 (a1|a2)&a3. Families:
  S  singles  : every non-C3 atom x 7 shapes x min-hold {1,5,21}           (C3-only rules are not generated: G1 rule 2)
  P  pairs    : 60,000; half (C3 atom, non-C3 atom), half (non-C3, non-C3), AND/OR 1:1, shape and min-hold uniform
  T  triples  : 30,000; (C3,C3,N) / (C3,N,N) / (N,N,N) 1:1:1, struct 3..6 uniform, shape and min-hold uniform
C3 atom draw: 25% C3 base signal atoms, 25% MS1 macro flag atoms, 50% other C3 (own-index price/vol/drawdown, GWZ svar/
dtoy/dtoat). Atoms inside one rule come from distinct primitives (macro flags / C3 signal: distinct (prim, transform)).
Every atom of a combination appears with its stored direction (both directions exist as separate atoms)."""
import json, numpy as np
SEED = 20261104
N_PAIRS, N_TRIPLES = 60000, 30000


def load_meta(path):
    return json.load(open(path))


def key(m):
    return (m['prim'], m['tr']) if m['prim'] in ('macro', 'c3sig') else (m['prim'],)


def generate(AM):
    import m1_engine as EN
    rng = np.random.default_rng(SEED)
    non = np.array([i for i, m in enumerate(AM) if not m['c3']], np.int64)
    c3s = np.array([i for i, m in enumerate(AM) if m['prim'] == 'c3sig'], np.int64)
    mac = np.array([i for i, m in enumerate(AM) if m['prim'] == 'macro'], np.int64)
    oth = np.array([i for i, m in enumerate(AM) if m['c3'] and m['prim'] not in ('macro', 'c3sig')], np.int64)
    K = [key(m) for m in AM]
    SC = EN.SHAPE_CODES; H = np.array(EN.HOLDS)
    rows = []; fam = []
    for a in non:
        for s in range(7):
            for h in H:
                rows.append((a, -1, -1, 0, SC[s, 0], SC[s, 1], h)); fam.append(0)

    def c3draw():
        u = rng.random()
        pool = c3s if u < 0.25 else (mac if u < 0.5 else oth)
        return int(pool[rng.integers(len(pool))])

    def ndraw():
        return int(non[rng.integers(len(non))])

    def distinct(ids):
        ks = [K[i] for i in ids]; return len(set(ks)) == len(ks)
    n = 0
    while n < N_PAIRS:
        if rng.random() < 0.5: ids = [c3draw(), ndraw()]
        else: ids = [ndraw(), ndraw()]
        op = 1 if rng.random() < 0.5 else 2
        s = int(rng.integers(7)); h = int(H[rng.integers(3)])
        if not distinct(ids):
            continue
        rows.append((ids[0], ids[1], -1, op, SC[s, 0], SC[s, 1], h)); fam.append(1); n += 1
    n = 0
    while n < N_TRIPLES:
        u = rng.random()
        if u < 1 / 3: ids = [c3draw(), c3draw(), ndraw()]
        elif u < 2 / 3: ids = [c3draw(), ndraw(), ndraw()]
        else: ids = [ndraw(), ndraw(), ndraw()]
        st = int(rng.integers(3, 7)); s = int(rng.integers(7)); h = int(H[rng.integers(3)])
        if not distinct(ids):
            continue
        perm = rng.permutation(3); ids = [ids[p] for p in perm]
        rows.append((ids[0], ids[1], ids[2], st, SC[s, 0], SC[s, 1], h)); fam.append(2); n += 1
    return np.array(rows, np.int64), np.array(fam, np.int8)


def describe(AM, row):
    names = {0: '', 1: 'AND', 2: 'OR', 3: 'AND3', 4: 'OR3', 5: '(a&b)|c', 6: '(a|b)&c'}
    lev = {0: '3x', 1: '2x', 2: '1x', 3: 'cash', 4: '-1x'}
    def at(i):
        m = AM[i]; q = '' if m['q'] == 0 else '@q%.1f' % m['q']
        return '%s.%s%s%s' % (m['prim'], m['tr'], m['dir'], q)
    a = [at(i) for i in row[:3] if i >= 0]
    st = int(row[3])
    if st == 0: e = a[0]
    elif st in (1, 2): e = '(%s %s %s)' % (a[0], names[st], a[1])
    elif st == 3: e = '(%s AND %s AND %s)' % tuple(a)
    elif st == 4: e = '(%s OR %s OR %s)' % tuple(a)
    elif st == 5: e = '((%s AND %s) OR %s)' % tuple(a)
    else: e = '((%s OR %s) AND %s)' % tuple(a)
    return '%s -> on %s / off %s, hold %d' % (e, lev[int(row[4])], lev[int(row[5])], int(row[6]))
