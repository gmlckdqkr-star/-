"""Audit F1 fix: 'bond excess 0' shift = mean(rb - rf) over the basis' SOURCE-DATA period (PRECOMMIT_DF1 s5), not over the
bootstrapped path days. Recomputes the DF2 adoption gates for tiers B and C and writes results/select_df2_fixed.json."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2, jp, iv
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
import mkt
rb = mkt.bond10(X).values if 'rb' not in X else X['rb'].values
ex_src = float(np.mean(rb[1:] - X['rf'].values[1:]))
mp = DC.market('dev250_path'); T = mp['r'].shape[1]; W = dfe.WARM
ex_path = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:]))
print('source-period excess/day %.4e (%.2f%%/yr) | path-days excess/day %.4e (%.2f%%/yr)' % (ex_src, ex_src * 252 * 100, ex_path, ex_path * 252 * 100))
m0 = dict(mp); m0['rb'] = mp['rb'] - ex_src
U = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; U.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
S = json.load(open('/mnt/project-files/research/df1/results/select_df2.json'))
def gv(i):
    cfg = U[i]['cfg']
    return float(np.median(dfe.stats(R2.run_cfg(cfg, m0), T)[0])), float(np.median(dfe.stats(R2.run_cfg(cfg, mp, cost=0.006), T)[0]))
out = dict(ex_src_per_day=ex_src, ex_path_per_day=ex_path, tiers={})
for t in ('B', 'C'):
    ub, d1 = S['tiers'][t]['union_best'], S['tiers'][t]['df1_best']
    g2, g1 = gv(ub), gv(d1); ok = g2[0] > g1[0] and g2[1] > g1[1]
    out['tiers'][t] = dict(union_best=ub, df1_best=d1, df2_bondx0=g2[0], df1_bondx0=g1[0], df2_cost2x=g2[1], df1_cost2x=g1[1], adopted=ub if ok else d1)
    print(t, out['tiers'][t])
json.dump(out, open('/mnt/project-files/research/df1/results/select_df2_fixed.json', 'w'), indent=1)
