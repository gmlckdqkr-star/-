"""AUDIT: third reading of 'bond excess 0' on dev250_path for the tier -40% DF2 gate (a): subtract each path's own mean (rb - rf)."""
import sys, os, json, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2
W = dfe.WARM; mp = DC.market('dev250_path'); T = mp['r'].shape[1]
U = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; U.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
exi = np.mean(mp['rb'][:, W:] - mp['rf'][:, W:], axis=1); m0 = dict(mp); m0['rb'] = mp['rb'] - exi[:, None]
out = dict(ex_per_path_p10_p50_p90=[float(x) for x in np.percentile(exi, [10, 50, 90])])
for tier, a, b in (('C', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'v1|s0.3|L1.0|K2|RB'), ('B', 'DF2|M2|b1|v1|s0.15|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB')):
    va = float(np.median(dfe.stats(R2.run_cfg(U[a]['cfg'], m0), T)[0])); vb = float(np.median(dfe.stats(R2.run_cfg(U[b]['cfg'], m0), T)[0]))
    out[tier] = dict(df2=va, df1=vb, a_margin_perpath=va - vb)
print(out); json.dump(out, open(sys.argv[1], 'w'), indent=1)
