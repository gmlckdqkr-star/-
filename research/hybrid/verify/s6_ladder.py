"""Verifier step 6 (check E): oracle ladder on dev250_path.
  (1) exact replicate: author's RNG/noise draws, MY truth labels and MY in-force schedule (decision at close k -> target at day k+2)
      -> must give the stored cagr exactly if the alignment is the same;
  (2) noise-model sensitivity at equal realized hit rate: symmetric (author), anchored (miss -> default s0.85, never a wrong switch),
      and magnitude envelopes (errors on the smallest / largest |block gap| blocks)."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np
import hyeng as H, ii

LAD = json.load(open('/mnt/project-files/research/hybrid/results/ladder_le2014.json'))
bn = 'dev250_path'
t0 = time.time()
TQ, DEP, CU, _ = H.ref(bn); S, SO = ii.arrays(bn)
P, T = TQ.shape
print('loaded', P, T, round(time.time() - t0, 1), 's', flush=True)
Lp = np.concatenate([CU[:, :1], CU[:, :-1]], axis=1) / 3.0
s085 = Lp * TQ + (1 - Lp) * DEP; s085[:, 0] = 0.0                    # precommit sleeve formula
ks = np.arange(0, T - 3, 21); nb = len(ks)


def block_sums(x):
    lx = np.log1p(np.maximum(x, -0.999999)); c = np.concatenate([np.zeros((P, 1)), np.cumsum(lx, 1)], 1)
    return np.stack([c[:, min(k + 24, T)] - c[:, min(k + 3, T)] for k in ks], 1)       # days k+3 .. k+23


def inforce(picks):
    """picks (P, nb) 0 = s0.85, 1 = partner, decided at close ks; target array value at day t = latest decision with k + 2 <= t"""
    dd = ks + 2; dd[0] = 0
    it = np.searchsorted(dd, np.arange(T), side='right') - 1
    A = (picks[:, it] == 0).astype(np.float64)
    return A, (1.0 - A)[:, :, None]


def cg(A, Wd, name):
    fin, EE, NT = H.run(bn, A, Wd, [name])
    return float(np.median(H.cagr(fin, T)))


res = {}
for sname, X in (('B2V', 'VALPROF4_L1'), ('B2B', 'BOND10_L3')):
    G0 = block_sums(s085); G1 = block_sums(S[:, :, H.sid(X)].astype(np.float64))
    truth = (G1 > G0).astype(int); base = float(np.mean(truth == 0)); gap = np.abs(G1 - G0)
    print(sname, 'base (always s0.85 hit) %.4f (stored %.4f)' % (base, LAD['%s|%s|0.50' % (bn, sname)]['base_s085']), flush=True)
    res[(sname, 'always_s085')] = cg(np.ones((P, T)), np.zeros((P, T, 1)), X)
    # (1) exact replicate with the author's draws
    for p in (0.60, 0.65, 0.70):
        rng = np.random.default_rng(int(p * 1000) + 7 * 1 + 0)
        ok = rng.random(truth.shape) < p; other = (truth + 1 + rng.integers(0, 1, size=truth.shape)) % 2
        pk = np.where(ok, truth, other)
        c = cg(*inforce(pk), X); st = LAD['%s|%s|%.2f' % (bn, sname, p)]['cagr']
        res[(sname, 'sym', p)] = (float(np.mean(pk == truth)), c)
        print('  symmetric p %.2f: hit %.4f cagr %.4f (stored %.4f)' % (p, np.mean(pk == truth), c, st), flush=True)
    # (2a) anchored: correct with prob q, otherwise default s0.85 -> hit = q + (1 - q) base
    for h in (0.60, 0.65, 0.70):
        q = (h - base) / (1 - base); rng = np.random.default_rng(1000 + int(h * 100))
        pk = np.where(rng.random(truth.shape) < q, truth, 0)
        c = cg(*inforce(pk), X); res[(sname, 'anch', h)] = (float(np.mean(pk == truth)), c)
        print('  anchored  hit %.4f: cagr %.4f' % (np.mean(pk == truth), c), flush=True)
    # (2b) envelopes at hit 0.65: per path, the 35% of blocks with the smallest (best case) / largest (worst case) gap are wrong
    for lab, order in (('errors_on_small_gaps', 1), ('errors_on_large_gaps', -1)):
        nerr = int(round(0.35 * nb)); pk = truth.copy()
        idx = np.argsort(order * gap, axis=1)[:, :nerr]
        np.put_along_axis(pk, idx, 1 - np.take_along_axis(truth, idx, 1), 1)
        c = cg(*inforce(pk), X); res[(sname, lab)] = (float(np.mean(pk == truth)), c)
        print('  %s hit %.4f: cagr %.4f' % (lab, np.mean(pk == truth), c), flush=True)
print('always s0.85 cagr', {k[0]: round(v, 4) for k, v in res.items() if k[1] == 'always_s085'})
print('total %.1f s' % (time.time() - t0))
