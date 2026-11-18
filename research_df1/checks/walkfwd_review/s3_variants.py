"""Reviewer: OOT summaries under three readings of the selection rule: code gate (walkfwd), text gate (source-period bond excess, audit F1),
no gate (task text: max pool median over all 1,123 configs). Uses walkfwd cache + gate_src.json. <=2014 only; pools NON-ACTUAL."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import run_grid as RG, run_df2 as R2
C = RG.configs() + R2.configs(); IDS = [c['id'] for c in C]; ix = {i: k for k, i in enumerate(IDS)}
CA = '/tmp/chk_walkfwd/cache/'; L = lambda f: dict(np.load(CA + f + '.npz'))
spx = L('spx2954'); RL = {'A': L('real_A'), 'B': L('real_B')}
o = json.load(open('/mnt/project-files/research/df1/checks/walkfwd/result.json')); G = json.load(open('/tmp/rev_walkfwd/gate_src.json'))
gs = {(r['seed'], r['dir'], r['tier']): r for r in G['rows']}
BUD = {'T25': -.25, 'T30': -.30, 'T40': -.40}
ALT_T40 = 'v1|s0.3|L1.0|K2|RB'
for d in ('A2B', 'B2A'):
    s, t = d[0], d[2]
    for tn in ('T25', 'T30', 'T40'):
        res = {}
        for seed in (7, 23, 41, 59, 101):
            PLs, PLt = L('pool_%s_s%d' % (s, seed)), L('pool_%s_s%d' % (t, seed))
            run = o['runs']['seed%d_%s' % (seed, d)][tn]
            wd = np.minimum(np.minimum(PLs['mdd_p10'], RL[s]['mdd']), spx['mdd']); ins = np.where(wd >= BUD[tn])[0]
            bv = PLs['cagr'][ins].max(); tie = ins[bv - PLs['cagr'][ins] < 0.0005]; u = IDS[int(tie[np.argmax(RL[s]['cagr'][tie])])]
            g = gs.get((seed, d, tn))
            picks = dict(code=run['pick'], text=g['adopt_src'] if g else run['pick'], nogate=u)
            assert (g is None) or g['adopt_path'] == run['pick']
            wdt = np.minimum(np.minimum(PLt['mdd_p10'], RL[t]['mdd']), spx['mdd']); inst = np.where(wdt >= BUD[tn])[0]
            for k, p in picks.items():
                j = ix[p]
                res.setdefault(k, []).append((p, RL[t]['cagr'][j], RL[t]['mdd'][j], PLt['cagr'][j], PLt['mdd_p10'][j],
                                              100 * np.mean(PLt['cagr'][inst] < PLt['cagr'][j] + 1e-12)))
            j = ix[ALT_T40]; res.setdefault('alt_T40_adopt', []).append((ALT_T40, RL[t]['cagr'][j], RL[t]['mdd'][j], PLt['cagr'][j], PLt['mdd_p10'][j], wd[j], wdt[j]))
        for k in ('code', 'text', 'nogate'):
            r = res[k]; pk = sorted(set(x[0] for x in r))
            print('%s %s %-6s picks %s | OOT real med %.4f worstMDD %.4f | pool med %.4f worst p10MDD %.4f | pool-def %d/5 real-def %d/5 | pct med %.1f' % (
                d, tn, k, {p: sum(x[0] == p for x in r) for p in pk}, np.median([x[1] for x in r]), min(x[2] for x in r), np.median([x[3] for x in r]),
                min(x[4] for x in r), sum(x[4] >= BUD[tn] for x in r), sum(x[2] >= BUD[tn] for x in r), np.median([x[5] for x in r])))
        if tn == 'T40':
            r = res['alt_T40_adopt']
            print('   %s (F1 text-reading adopted T40) on test %s: real %.4f/%.4f pool med %.4f p10MDD worst %.4f | WD sel-period %s | WD test-period %s' % (
                ALT_T40, t, r[0][1], r[0][2], np.median([x[3] for x in r]), min(x[4] for x in r), [round(x[5], 4) for x in r], [round(x[6], 4) for x in r]))
