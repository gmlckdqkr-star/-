"""Spot re-run of two parity points (constant weights): hyeng.run vs I_INTEGRATE ii.run (el._comb)."""
import os, sys
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np, hyeng as H, ii
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    for a0, w in [(0.4, {'VALPROF4_L1': 0.3, 'BOND10_L3': 0.3}), (0.5, {'BOND10_L1': 0.5})]:
        f1, E1 = ii.run(bn, a0, w); names = list(w); f2, E2, _ = H.run(bn, a0, np.array([w[n] for n in names]), names)
        print(bn, a0, w, 'ii %.6f hy %.6f maxlogdiff %.1e' % (np.median(H.cagr(f1, E1.shape[1])), np.median(H.cagr(f2, E2.shape[1])),
              np.max(np.abs(np.log(f1) - np.log(f2)))))
