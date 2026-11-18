import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2, jp, iv, mkt
sys.path.insert(1, '/tmp/rev_tails/tl'); import tails as TL
G = TL.G; W = dfe.WARM
mp = DC.market('dev250_path'); T = mp['r'].shape[1]; c0 = mp['ctx']; X = TL.X_of('dev250_path')
ex_path = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:]))
rb = mkt.bond10(X).values if 'rb' not in X else X['rb'].values
ex_src = float(np.mean(rb[1:] - X['rf'].values[1:]))
print('ex_path %.3e ex_src %.3e' % (ex_path, ex_src))
days = np.random.default_rng(23).integers(W + 1, T, size=mp['r'].shape[0])
mg = TL.gap_market(c0, X, days, -0.20)
def gv(i, m, ex):
    cfg = dict(G[i]['cfg']); m0 = dict(m); m0['rb'] = m['rb'] - ex
    return float(np.median(dfe.stats(R2.run_cfg(cfg, m0), T)[0])), float(np.median(dfe.stats(R2.run_cfg(cfg, m, cost=0.006), T)[0]))
pairs = {'T30_gap20': ('DF2|M2|b1|v1|s0.1|L1.0|K2|RB', 'v1|s0.1|L3.0|K2|RB'),
         'T40_gap20': ('DF2|M2|b1|v1|s0.2|L1.0|K2|RB', 'v1|s0.3|L1.0|K2|RB'),
         'T30_delay4': ('DF2|M2|b1|v1|s0.2|L1.0|K1|RB', 'v1|s0.15|L1.0|K1|RB'),
         'T40_orig_C': ('DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'v1|s0.3|L1.0|K2|RB')}
out = {}
for nm, (u, d1) in pairs.items():
    for lab, m, ex in (('base_expath', mp, ex_path), ('base_exsrc', mp, ex_src), ('gap20_exsrc', mg, ex_src)):
        if nm == 'T30_delay4' and lab == 'gap20_exsrc': continue
        a, b = gv(u, m, ex), gv(d1, m, ex); ok = a[0] > b[0] and a[1] > b[1]
        out['%s|%s' % (nm, lab)] = dict(df2=u, df1=d1, df2_bondx0=a[0], df1_bondx0=b[0], df2_cost2x=a[1], df1_cost2x=b[1], df2_passes=ok)
        print('%-11s %-12s DF2 bx0 %.4f c2x %.4f | DF1 bx0 %.4f c2x %.4f -> %s' % (nm, lab, a[0], a[1], b[0], b[1], 'PASS' if ok else 'FAIL (DF1 kept)'), flush=True)
for i in ('v1|s0.1|L3.0|K2|RB', 'DF2|M2|b1|v1|s0.1|L1.0|K2|RB', 'DF2|M2|b1|v1|s0.2|L1.0|K2|RB', 'v1|s0.3|L1.0|K2|RB'):
    g = G[i]; print(i, 'base path %.4f p10 %.4f ndx %.4f spx %.4f' % (g['dev250_path']['cagr'], g['dev250_path']['mdd_p10'], g['real_ndx_86_14']['mdd'], g['real_spx_29_54']['mdd']))
json.dump(out, open('/tmp/rev_tails/rev2.json', 'w'), indent=1)
