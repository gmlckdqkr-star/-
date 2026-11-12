"""JS1 causality test of the builder: atoms at (c, t) must not change when all data dated after t is deleted."""
import sys, numpy as np; sys.path.insert(0, '/home/user/repo/research_js1/code')
import js1_build as B
S = B.load(); F = B.features(S); W = B.world(F); names, A = B.build_atoms(F, W)
bad = 0
for T in (1913, 1950, 1985, 2007):
    k = T - B.Y0; S2 = {kk: np.where(np.arange(B.NY)[None, :] > k, np.nan, v) for kk, v in S.items()}
    F2 = B.features(S2); W2 = B.world(F2); n2, A2 = B.build_atoms(F2, W2)
    assert n2 == names
    d = (A[:, :, k] != A2[:, :, k]).sum(); bad += d
    print('cut at', T, 'atom mismatches at t=T:', d, ' (all earlier years:', (A[:, :, :k + 1] != A2[:, :, :k + 1]).sum(), ')')
print('TOTAL mismatches', bad); assert bad == 0
