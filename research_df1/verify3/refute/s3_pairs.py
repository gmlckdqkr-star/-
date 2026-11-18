import os, sys, time, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std'); os.environ.setdefault('NUMBA_NUM_THREADS','2')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
t0 = time.time()
EX = 1.3988294390226633e-4
G1 = json.load(open('/mnt/project-files/research/df1/results/grid.json')); G2 = json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))
OLD = dict(G1['configs']); OLD.update(G2['configs'])
mp = DC.market('dev250_path'); W = dfe.WARM
print('path-realised mean (rb-rf) %.4e (%.2f%%/yr) vs EX %.2f%%/yr' % (np.mean(mp['rb'][:, W+1:] - mp['rf'][:, W+1:]), np.mean(mp['rb'][:, W+1:] - mp['rf'][:, W+1:])*25200, EX*25200))
mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX
T = mp['r'].shape[1]
def per(cfg, m):
    o = R2.run_cfg(cfg, m); cg, md = dfe.stats(o, T); return cg, md, o[:, 4]
res = {}
for cid in ('v1|s0.3|L1.0|K2|RB', 'DF2|M0|b3|v1|s0.3|L1.0|K2|RB'):
    res[cid] = dict(P=per(OLD[cid]['cfg'], mp), P0=per(OLD[cid]['cfg'], mp0))
    print(cid, 'P med %.5f  P0 med %.5f  ntr med %.0f' % (np.median(res[cid]['P'][0]), np.median(res[cid]['P0'][0]), np.median(res[cid]['P'][2])), '%.0fs' % (time.time()-t0))
a, b = res['DF2|M0|b3|v1|s0.3|L1.0|K2|RB'], res['v1|s0.3|L1.0|K2|RB']
for k in ('P', 'P0'):
    d = a[k][0] - b[k][0]; dm = a[k][1] - b[k][1]
    print(k, 'W40-T40: diff of medians %.4f pp | median paired diff %.4f pp | p10 %.4f p90 %.4f | share W40>T40 %.3f | mdd paired median %.4f pp, share W40 mdd worse %.3f' % (
        100*(np.median(a[k][0]) - np.median(b[k][0])), 100*np.median(d), 100*np.percentile(d, 10), 100*np.percentile(d, 90), np.mean(d > 0), 100*np.median(dm), np.mean(dm < 0)))
np.savez('/tmp/vf_refute/w40t40.npz', **{k.replace('|','_')+'_'+b_+'_'+str(j): v[b_][j] for k, v in res.items() for b_ in ('P','P0') for j in range(3)})
