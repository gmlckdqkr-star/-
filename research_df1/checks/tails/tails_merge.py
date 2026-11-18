"""Merge stage JSONs into result.json (check 'tails'). <=2014 only; gap rows are NON-ACTUAL (synthetic stress)."""
import json, numpy as np
D = '/mnt/project-files/research/df1/checks/tails'
L = lambda f: json.load(open(D + '/' + f))
dl, cr, gp, sc, rg, rd = L('stage_delay.json'), L('stage_creep.json'), L('stage_gap.json'), L('stage_scan.json'), L('stage_resel_gap.json'), L('stage_resel_delay.json')
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'T40alt_df1': 'v1|s0.3|L1.0|K2|RB'}
LIM = {'T25': -0.25, 'T30': -0.30, 'T40': -0.40, 'T40alt_df1': -0.40}
R = dict(id='tails', data_end='2014-12-31', picks=PICKS, tier_limit=LIM,
         notes=['gap rows are NON-ACTUAL: one real day per path overwritten by -20% or -25% NDX (3x product = 3r-2rf-er3 -> about -60%/-75%); bond, rf, macro flags unchanged; signals rebuilt',
                'WD = min(dev250_path MDD p10, real NDX 86-14 MDD, real SPX 29-54 MDD); gap WD uses gap-path p10 with the unchanged real-base MDDs',
                'recording engine = dfe.run1 source verbatim + weight record; parity vs dfe.run max abs diff 0 on all picks and bases',
                're-selection rows are diagnostics (DF2 adoption gates not re-run); not the pre-registered rule'])
R['delay'] = {pk: {d: dl['table']['%s|d%d' % (pk, d)] for d in (1, 2, 3, 4, 5)} for pk in PICKS}
R['gap_path'] = {}
for s, rows in gp['scen'].items():
    R['gap_path'][s] = {k: {a: b for a, b in v.items()} for k, v in rows.items()}
R['gap_real_scan'] = sc
R['creep'] = cr
R['reselect_gap'] = rg; R['reselect_delay'] = rd
# replacement configs' base (no stress) values
rep = set()
for blk in (rg, rd):
    for s, tiers in blk.items():
        for tn, t in tiers.items():
            for k in ('union_best', 'df1_best'):
                if t.get(k): rep.add(t[k])
R['replacement_base_rows'] = {i: dict(path=G[i]['dev250_path']['cagr'], p10=G[i]['dev250_path']['mdd_p10'], ndx_mdd=G[i]['real_ndx_86_14']['mdd'],
                                      spx_mdd=G[i]['real_spx_29_54']['mdd'], WD=min(G[i]['dev250_path']['mdd_p10'], G[i]['real_ndx_86_14']['mdd'], G[i]['real_spx_29_54']['mdd']))
                              for i in sorted(rep)}
for i, v in R['replacement_base_rows'].items(): print('%-34s base path %.4f WD %.4f' % (i, v['path'], v['WD']))
for s in ('base', 'gap20_s23', 'gap25_s23'):
    print(s, {tn: (t['n_in_union'], t['n_in_df1']) for tn, t in rg[s].items()})
for s in rd: print(s, {tn: (t['n_in_union'], t['n_in_df1']) for tn, t in rd[s].items()})
# gap + delay combos
for s in ('rand_s23|g20', 'rand_s23|g25', 'invested_s23|g20', 'invested_s23|g25'):
    for pk in PICKS:
        a = gp['scen'][s][pk]
        print('%-18s %-11s d2 path %.4f WD %.4f | d3 path %.4f WD %.4f | d5 path %.4f WD %.4f' % (s, pk, a['cagr_med'], a['WD'], a['delay3']['cagr_med'], a['delay3']['WD'], a['delay5']['cagr_med'], a['delay5']['WD']))
json.dump(R, open(D + '/result.json', 'w'), indent=1)
print('written')
