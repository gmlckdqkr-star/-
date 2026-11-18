import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
W = dfe.WARM
C = {c['id']: c for c in RG.configs()}; C.update({c['id']: c for c in R2.configs()})
M = {b: DC.market(b) for b in ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')}
def ev(cid, **kw):
    r = {}
    for b, m in M.items():
        T = m['r'].shape[1]; cg, md = dfe.stats(R2.run_cfg(C[cid], m, **kw), T)
        r[b] = (float(np.median(cg)), float(np.percentile(md, 10))) if b == 'dev250_path' else (float(cg[0]), float(md[0]))
    wd = min(r['dev250_path'][1], r['real_ndx_86_14'][1], r['real_spx_29_54'][1])
    return r, wd
for cid, kw in (('v1|s0.1|L1.0|K1|RB', dict(cost=0.0045)), ('v1|s0.2|L1.0|K1|RB', dict(D=2.5e6/30e6)), ('v1|s0.2|L1.0|K1|RB', dict(erb=0.0025)),
                ('v1|s0.3|L1.5|K2|RB', dict(cost=0.002)), ('v1|s0.3|L1.5|K2|RB', {})):
    r, wd = ev(cid, **kw); print(cid, kw, {k: tuple(round(x, 5) for x in v) for k, v in r.items()}, 'WD %.5f' % wd)
mp = M['dev250_path']; T = mp['r'].shape[1]
ex = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:])); m0 = dict(mp); m0['rb'] = mp['rb'] - ex
for cid in ('DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'v1|s0.3|L1.5|K2|RB'):
    a = float(np.median(dfe.stats(R2.run_cfg(C[cid], m0, cost=0.002), T)[0])); b = float(np.median(dfe.stats(R2.run_cfg(C[cid], mp, cost=0.004), T)[0]))
    print('cost020 gate(path ex)', cid, 'bondx0 %.5f cost2x %.5f' % (a, b))
