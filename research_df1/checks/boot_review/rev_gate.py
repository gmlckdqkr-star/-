"""Reviewer re-run for check 'boot': recompute the DF2 bond-excess-0 gate with the SOURCE-PERIOD mean (rb - rf) of
1986-01-02..2014-12-31 (PRECOMMIT_DF1 s5 text; same as code/gate_fix.py -> results/select_df2_fixed.json) instead of each
bootstrap pool's own path-day mean, and redo adoption per pool + on the pooled block-250 basis. <=2014 data only; NON-ACTUAL paths."""
import os, sys, json, numpy as np
os.environ['BOOT_CACHE'] = '/tmp/rev_boot/cache/'
sys.path.insert(0, '/tmp/rev_boot')
import bp as BP, dfe, run_df2 as R2, jp, iv, mkt

PD = '/mnt/project-files/research/df1/checks/boot/'
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
rb = mkt.bond10(X).values if 'rb' not in X else X['rb'].values
EX_SRC = float(np.mean(rb[1:] - X['rf'].values[1:]))
print('EX_SRC per day %.6e  (%.3f%%/yr)' % (EX_SRC, EX_SRC * 252 * 100), flush=True)

def gate(i, m, T, ex):
    m0 = dict(m); m0['rb'] = m['rb'] - ex
    return dfe.stats(R2.run_cfg(BP.CFG[i], m0), T)[0], dfe.stats(R2.run_cfg(BP.CFG[i], m, cost=0.006), T)[0]

out = dict(ex_src=EX_SRC, pools={}, pooled={})
TT = dict(BP.TIERS)
PER = {}   # per-path arrays for pooled gate: (pool, cfg) -> (bx0_src, cost2x)
for nm in BP.POOLS:
    r = json.load(open(PD + 'pools/pool_%s.json' % nm)); tab = r['tab']
    m = BP.build(*BP.POOLS[nm]); T = m['r'].shape[1]; W = dfe.WARM
    ex_path = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:]))
    res = dict(ex_path=ex_path)
    need = set()
    for tn in ('T25', 'T30', 'T40'):
        s = r['sel'][tn]; ub, d1 = s.get('union_best'), s.get('df1_best')
        if ub and BP.CFG[ub]['fam'] == 'df2' and d1: need |= {ub, d1}
    if nm in ('base_s7_b250', 's11_b250', 's23_b250', 's37_b250', 's51_b250'):
        need |= {'DF2|M2|b1|v1|s0.2|L1.0|K1|RB', 'v1|s0.2|L1.0|K1|RB', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'v1|s0.3|L1.0|K2|RB'}
    G = {}
    for i in need:
        bx_src, c2 = gate(i, m, T, EX_SRC); bx_path, _ = gate(i, m, T, ex_path)
        G[i] = dict(bx0_src=float(np.median(bx_src)), bx0_path=float(np.median(bx_path)), cost2x=float(np.median(c2)))
        PER[(nm, i)] = (bx_src, c2)
    for tn in ('T25', 'T30', 'T40'):
        s = r['sel'][tn]; ub, d1 = s.get('union_best'), s.get('df1_best'); t = dict(union_best=ub, df1_best=d1, adopted_check=s.get('adopted'))
        if ub and BP.CFG[ub]['fam'] == 'df2' and d1:
            g2, g1 = G[ub], G[d1]
            t.update(bx0_path=(g2['bx0_path'], g1['bx0_path']), bx0_src=(g2['bx0_src'], g1['bx0_src']), cost2x=(g2['cost2x'], g1['cost2x']),
                     margin_path_pp=100 * (g2['bx0_path'] - g1['bx0_path']), margin_src_pp=100 * (g2['bx0_src'] - g1['bx0_src']))
            ok = g2['bx0_src'] > g1['bx0_src'] and g2['cost2x'] > g1['cost2x']
            t['adopted_src'] = ub if ok else d1
        else:
            t['adopted_src'] = s.get('adopted')
        t['adopted_src_cagr'] = tab[t['adopted_src']]['cagr'] if t['adopted_src'] else None
        res[tn] = t
    res['G'] = G
    out['pools'][nm] = res
    print(nm, 'ex_path %.4e' % ex_path, flush=True)
    for tn in ('T25', 'T30', 'T40'):
        t = res[tn]; print('  %s ub %s d1 %s | check adopted %s | margin path %s src %s | adopted(src) %s %.4f' % (
            tn, t['union_best'], t['df1_best'], t['adopted_check'], None if 'margin_path_pp' not in t else round(t['margin_path_pp'], 3),
            None if 'margin_src_pp' not in t else round(t['margin_src_pp'], 3), t['adopted_src'], t['adopted_src_cagr'] or 0), flush=True)
    for i, g in G.items(): print('     %-34s bx0_src %.5f bx0_path %.5f cost2x %.5f' % (i, g['bx0_src'], g['bx0_path'], g['cost2x']))
    del m

# pooled block-250 basis (5 pools x 500 paths), gate with source-period ex
pl = json.load(open(PD + 'pooled_b250.json'))
USE = ('base_s7_b250', 's11_b250', 's23_b250', 's37_b250', 's51_b250')
for tn in ('T30', 'T40'):
    t = pl['tiers'][tn]; ub, d1 = t['union_best'], t['df1_best']
    g2 = [np.median(np.concatenate([PER[(n, i)][k] for n in USE])) for i in (ub, d1) for k in (0, 1)]
    ok = g2[0] > g2[2] and g2[1] > g2[3]
    out['pooled'][tn] = dict(union_best=ub, df1_best=d1, bx0_src=(float(g2[0]), float(g2[2])), cost2x=(float(g2[1]), float(g2[3])),
                             margin_src_pp=100 * float(g2[0] - g2[2]), check_gate=t.get('gate'), adopted_check=t['adopted'],
                             adopted_src=ub if ok else d1, adopted_src_cagr=t['union_best_cagr'] if ok else t['df1_best_cagr'])
    print('pooled', tn, json.dumps(out['pooled'][tn]), flush=True)
json.dump(out, open('/tmp/rev_boot/rev_gate.json', 'w'), indent=1)
