# builder check: the walkfwd pool builder with the full 1986-2014 window and seed 7 must reproduce DC.market('dev250_path') exactly
import sys, numpy as np
sys.path.insert(0, '/tmp/chk_walkfwd'); sys.path.insert(0, '/mnt/project-files/research/df1/code')
import walkfwd as WF, dfctx as DC, dfe, run_df2 as R2
WF.PER['F'] = ('1986-01-02', '2014-12-31'); m = WF.pool('F', 7); md = DC.market('dev250_path')
print('max|dr|', float(np.abs(m['r'] - md['r']).max()), 'st_v1 equal', bool((m['st_v1'] == md['st_v1']).all()), 'st_al equal', bool((m['st_al'] == md['st_al']).all()))
T = m['r'].shape[1]
for i in ('v1|s0.1|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'):
    cfg = [c for c in WF.C if c['id'] == i][0]; cg, mm = dfe.stats(R2.run_cfg(cfg, m), T)
    print(i, 'path median %.4f mdd_p10 %.4f' % (np.median(cg), np.percentile(mm, 10)))
