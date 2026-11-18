"""DF1 section 5 rows for the tier picks: glued upper bound, SPX29 fill B, sensitivities (delay 3, cost 2x, MS1 cash,
bond excess 0), risk-off swaps (RB -> RT / RC) for contribution. Writes results/robust.json. <=2014 only."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
S = json.load(open('/mnt/project-files/research/df1/results/select.json'))
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']
picks = {t: S['tiers'][t]['best'] for t in ('A_fallback_25', 'B', 'C') if S['tiers'][t]['best']}
BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_29_54', 'real_spx_29_54_B', 'real_spx_55_85', 'real_spx_70_85',
         'UK', 'CA', 'AU', 'DE', 'FR', 'JP')
SENS = {'base': {}, 'delay3': dict(delay=3), 'cost2x': dict(cost=0.006), 'ms1cash': dict(cspr=0.02), 'bondx0': 'bondx0'}
W = dfe.WARM
out = dict(picks=picks, rows={})
for bn in BASES:
    m = DC.market(bn); T = m['r'].shape[1]; path = m['r'].shape[0] > 1
    ex = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:])); m0 = dict(m); m0['rb'] = m['rb'] - ex
    for t, i in picks.items():
        cfg = dict(G[i]['cfg'])
        for sn, kw in SENS.items():
            if sn != 'base' and bn in ('dev250_glued', 'real_spx_29_54_B'): continue
            if sn == 'bondx0': o = RG.run_cfg(cfg, m0)
            else: o = RG.run_cfg(cfg, m, **kw)
            out['rows']['%s|%s|%s' % (t, bn, sn)] = RG.summ(o, T, path)
        for ro in ('RT', 'RC'):
            c2 = dict(cfg); c2['roff'] = ro
            out['rows']['%s|%s|swap_%s' % (t, bn, ro)] = RG.summ(RG.run_cfg(c2, m), T, path)
        out['rows']['%s|%s|bondx0_excess' % (t, bn)] = dict(excess_removed=ex)
    print(bn, 'done', flush=True)
json.dump(out, open('/mnt/project-files/research/df1/results/robust.json', 'w'), indent=1)
for t in picks:
    print('==', t, picks[t])
    for bn in BASES:
        r = out['rows']
        def g(s): k = '%s|%s|%s' % (t, bn, s); return ('%.4f/%.3f' % (r[k]['cagr'], r[k].get('mdd_p10', r[k]['mdd']))) if k in r else '-'
        print('  %-17s base %s | d3 %s | c2 %s | ms1cash %s | bondx0 %s | RT %s | RC %s' % (bn, g('base'), g('delay3'), g('cost2x'), g('ms1cash'), g('bondx0'), g('swap_RT'), g('swap_RC')))
