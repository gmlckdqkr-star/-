"""Verifier step 7 (check E): exact replicates of stored ladder points on the real bases (P = 1 tiled x 40 seeds), incl. the BK4
addendum extension, with the author's RNG draws but MY truth labels, MY in-force schedule and my own engine call (H._dyn)."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np
import hyeng as H, ii

LAD = json.load(open('/mnt/project-files/research/hybrid/results/ladder_le2014.json'))
SETS = {'B2V': ['VALPROF4_L1'], 'B2B': ['BOND10_L3'], 'BK4': ['VALPROF4_L1', 'BOND10_L3', 'SPXH_L1']}
POINTS = [('real_ndx_86_14', 'B2V', 0.65), ('real_ndx_86_14', 'B2B', 0.60), ('real_ndx_86_14', 'BK4', 0.40), ('real_ndx_86_14', 'BK4', 0.70),
          ('real_spx_55_85', 'B2B', 0.80), ('real_spx_55_85', 'BK4', 0.45), ('real_spx_55_85', 'B2V', 0.90)]
SEEDS = 40
for bn, sname, p in POINTS:
    names = SETS[sname]
    TQ, DEP, CU, _ = H.ref(bn); S, SO = ii.arrays(bn); T = TQ.shape[1]
    Lp = np.r_[CU[0, 0], CU[0, :-1]] / 3.0; s085 = Lp * TQ[0] + (1 - Lp) * DEP[0]; s085[0] = 0.0
    X = np.stack([s085] + [S[0, :, H.sid(n)].astype(np.float64) for n in names], 1)          # (T, M)
    M = X.shape[1]; lx = np.log1p(np.maximum(X, -0.999999))
    ks = np.arange(0, T - 3, 21)
    G = np.stack([lx[k + 3:k + 24].sum(0) for k in ks])                                         # days k+3..k+23
    truth = np.argmax(G, 1)
    tr = np.repeat(truth[None], SEEDS, 0)
    rng = np.random.default_rng(int(p * 1000) + 7 * len(names) + (0 if bn == 'dev250_path' else 99))
    ok = rng.random(tr.shape) < p; other = (tr + 1 + rng.integers(0, M - 1, size=tr.shape)) % M; pk = np.where(ok, tr, other)
    dd = ks + 2; dd[0] = 0; it = np.searchsorted(dd, np.arange(T), side='right') - 1
    PK = pk[:, it]                                                                              # (Q, T) in-force candidate
    A = (PK == 0).astype(np.float64)
    order = np.argsort([H.sid(n) for n in names], kind='stable')                                  # engine wants SID order
    Wd = np.stack([(PK == j + 1).astype(np.float64) for j in order], 2)
    idx = [H.sid(names[j]) for j in order]
    Sa = np.repeat(S[:, :, idx].astype(np.float64), SEEDS, 0); SOa = np.repeat(SO[:, :, idx].astype(np.float64), SEEDS, 0)
    rep = lambda a: np.ascontiguousarray(np.repeat(a, SEEDS, 0))
    fin, EE, NT = H._dyn(rep(TQ), rep(DEP), rep(CU), np.ascontiguousarray(Sa), np.ascontiguousarray(SOa), np.ascontiguousarray(A),
                         np.ascontiguousarray(Wd), 0.003, H.PP['tax'], H.DED, int(H.PP['harvest']), H.PP['hthr'], 21, 0.05, 0.25)
    c = float(np.median(H.cagr(fin, T))); st = LAD['%s|%s|%.2f' % (bn, sname, p)]
    print('%s %s p=%.2f: hit %.4f (stored %.4f) cagr %.6f (stored %.6f) base %.4f (stored %.4f)' % (
        bn, sname, p, np.mean(pk == tr), st['hit_realized'], c, st['cagr'], np.mean(truth == 0), st['base_s085']), flush=True)
