"""Reviewer: re-derive walkfwd selections from cached per-config arrays (no gate), and inspect T25 / tier-edge facts. <=2014 only."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import run_grid as RG, run_df2 as R2
C = RG.configs() + R2.configs(); IDS = [c['id'] for c in C]; ISDF2 = np.array([c.get('fam') == 'df2' for c in C])
CA = '/tmp/chk_walkfwd/cache/'
L = lambda f: dict(np.load(CA + f + '.npz'))
spx = L('spx2954'); RL = {'A': L('real_A'), 'B': L('real_B')}
ix = {i: k for k, i in enumerate(IDS)}
def sel(pl, rl, bud, mask=None):
    wd = np.minimum(np.minimum(pl['mdd_p10'], rl['mdd']), spx['mdd'])
    ok = wd >= bud
    if mask is not None: ok &= mask
    ins = np.where(ok)[0]
    if not len(ins): return None, wd, ins
    bv = pl['cagr'][ins].max(); tie = ins[bv - pl['cagr'][ins] < 0.0005]; return int(tie[np.argmax(rl['cagr'][tie])]), wd, ins
for seed in (7, 23, 41, 59, 101):
    PL = {p: L('pool_%s_s%d' % (p, seed)) for p in 'AB'}
    for s, t in (('A', 'B'), ('B', 'A')):
        for tn, bud in (('T25', -.25), ('T30', -.30), ('T40', -.40)):
            u, wd, ins = sel(PL[s], RL[s], bud); d, _, _ = sel(PL[s], RL[s], bud, ~ISDF2)
            print(seed, s + '2' + t, tn, 'n_in', len(ins), 'union', IDS[u], 'df1', IDS[d],
                  '| df1 OOT real %.4f/%.4f pool %.4f/%.4f' % (RL[t]['cagr'][d], RL[t]['mdd'][d], PL[t]['cagr'][d], PL[t]['mdd_p10'][d]))
    # T25 detail on A: adopted RB vs RT pick: pool medians, components of WD
    for i in ('v1|s0.1|L1.0|K1|RB', 'v1|s0.1|L1.0|K1|RT', 'v1|s0.1|L1.0|K1|RBT', 'v1|s0.1|L1.0|K1|RC'):
        j = ix[i]
        print('   A-pool %-22s med %.4f p10mdd %.4f realA %.4f/%.4f spx %.4f | B-pool med %.4f p10mdd %.4f realB %.4f/%.4f' % (
            i, PL['A']['cagr'][j], PL['A']['mdd_p10'][j], RL['A']['cagr'][j], RL['A']['mdd'][j], spx['mdd'][j], PL['B']['cagr'][j], PL['B']['mdd_p10'][j], RL['B']['cagr'][j], RL['B']['mdd'][j]))
    for i in ('v1|s0.2|L1.0|K1|RB', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'v1|s0.3|L1.0|K2|RB', 'v1|s0.15|L1.0|K1|RB'):
        j = ix[i]
        print('   %-30s A-pool med %.4f p10mdd %.4f realA %.4f/%.4f spx %.4f | B-pool med %.4f p10mdd %.4f realB %.4f/%.4f' % (
            i, PL['A']['cagr'][j], PL['A']['mdd_p10'][j], RL['A']['cagr'][j], RL['A']['mdd'][j], spx['mdd'][j], PL['B']['cagr'][j], PL['B']['mdd_p10'][j], RL['B']['cagr'][j], RL['B']['mdd'][j]))
