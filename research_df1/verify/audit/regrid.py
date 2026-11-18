"""AUDIT: dfe.py was modified (03:30) after grid.json was written (03:27). Re-run every DF1 config (and a sample of DF2 configs)
with the current engine on all 11 bases and compare every summary field with results/grid.json / grid_df2.json. <=2014 only."""
import sys, os, json, time, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
R = '/mnt/project-files/research/df1/results/'
G1 = json.load(open(R + 'grid.json')); G2 = json.load(open(R + 'grid_df2.json'))['configs']
C1 = RG.configs(); g = np.random.default_rng(5); ids2 = sorted(G2); samp = [ids2[j] for j in g.choice(len(ids2), 60, replace=False)]
C2 = [G2[i]['cfg'] for i in samp]
mx1 = {}; mx2 = {}; refd = {}; t0 = time.time()
for bn in RG.BASES:
    m = DC.market(bn); T = m['r'].shape[1]; path = m['r'].shape[0] > 1
    for cfg in C1:
        s = RG.summ(RG.run_cfg(cfg, m), T, path); r = G1['configs'][cfg['id']][bn]
        for k, v in s.items(): mx1[k] = max(mx1.get(k, 0.0), abs(v - r[k]))
    for cfg in C2:
        s = RG.summ(R2.run_cfg(cfg, m), T, path); r = G2[cfg['id']][bn]
        for k, v in s.items(): mx2[k] = max(mx2.get(k, 0.0), abs(v - r[k]))
    rr = RG.refs(m)
    for nm in ('hold1x_QQQ', 'hold3x_TQQQ', 'v1_locked_cash0'):
        refd['%s|%s' % (bn, nm)] = abs(rr[nm]['cagr'] - G1['refs'][bn][nm]['cagr'])
    print(bn, 'done %.0fs' % (time.time() - t0), flush=True)
    if bn == 'dev250_path': DC._M.pop(bn, None)
out = dict(df1_all483_maxabs=mx1, df2_sample60_maxabs=mx2, refs_cagr_absdiff_max=max(refd.values()))
print(out); json.dump(out, open(sys.argv[1], 'w'), indent=1)
