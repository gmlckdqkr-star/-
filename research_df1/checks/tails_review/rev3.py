import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2, mkt
sys.path.insert(1, '/tmp/rev_tails/tl'); import tails as TL
G = TL.G; W = dfe.WARM
wd = lambda g: min(g['dev250_path']['mdd_p10'], g['real_ndx_86_14']['mdd'], g['real_spx_29_54']['mdd'])
for i in ('DF2|M0|b2|v1|s0.1|L1.0|K1|RB', 'DF2|M2|b1|v1|s0.2|L1.0|K1|RB', 'v1|s0.1|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB'):
    g = G[i]; print('%-32s d2 path %.4f p10 %.4f ndx %.4f spx %.4f WD %.4f' % (i, g['dev250_path']['cagr'], g['dev250_path']['mdd_p10'], g['real_ndx_86_14']['mdd'], g['real_spx_29_54']['mdd'], wd(g)))
mp = DC.market('dev250_path'); T = mp['r'].shape[1]; X = TL.X_of('dev250_path')
ex_path = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:]))
rb = mkt.bond10(X).values if 'rb' not in X else X['rb'].values
ex_src = float(np.mean(rb[1:] - X['rf'].values[1:]))
def gv(i, ex, d):
    cfg = dict(G[i]['cfg']); m0 = dict(mp); m0['rb'] = mp['rb'] - ex
    return float(np.median(dfe.stats(R2.run_cfg(cfg, m0, delay=d), T)[0])), float(np.median(dfe.stats(R2.run_cfg(cfg, mp, cost=0.006, delay=d), T)[0]))
pairs = {'T25_d1': ('DF2|M0|b2|v1|s0.1|L1.0|K1|RB', 'v1|s0.1|L1.0|K1|RB', 1),
         'T30_d1': ('DF2|M2|b1|v1|s0.2|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB', 1),
         'T30_d3': ('DF2|M2|b1|v1|s0.2|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB', 3)}
out = {}
for nm, (u, d1, d) in pairs.items():
    for lab, ex in (('expath', ex_path), ('exsrc', ex_src)):
        a, b = gv(u, ex, d), gv(d1, ex, d); ok = a[0] > b[0] and a[1] > b[1]
        out['%s|%s' % (nm, lab)] = dict(df2=u, df1=d1, delay=d, df2_bondx0=a[0], df1_bondx0=b[0], df2_cost2x=a[1], df1_cost2x=b[1], df2_passes=ok)
        print('%-7s %-7s DF2 bx0 %.4f c2x %.4f | DF1 bx0 %.4f c2x %.4f -> %s' % (nm, lab, a[0], a[1], b[0], b[1], 'PASS (flip to DF2)' if ok else 'FAIL (DF1 kept)'), flush=True)
json.dump(out, open('/tmp/rev_tails/rev3.json', 'w'), indent=1)
