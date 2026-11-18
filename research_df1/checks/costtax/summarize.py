"""Builds checks/costtax/result.json from resel_<variant>.json, picks_krw.json, krw_reselect.json. <=2014 only."""
import json, os, numpy as np
D = '/mnt/project-files/research/df1/checks/costtax/'
VARS = ['base', 'W0_30M', 'W0_100M', 'W0_300M', 'bond7y', 'bondER25', 'harvest0', 'cost020', 'cost045', 'combo_mid', 'combo_adv']
SINGLE = ['W0_30M', 'W0_100M', 'W0_300M', 'bond7y', 'bondER25', 'harvest0', 'cost020', 'cost045']
BUD = {'T25': -0.25, 'T30': -0.30, 'T40': -0.40, 'T40_gatefix': -0.40}
TKEY = {'T25': 'T25', 'T30': 'T30', 'T40': 'T40', 'T40_gatefix': 'T40'}
PK = json.load(open(D + 'picks_krw.json')); KR = json.load(open(D + 'krw_reselect.json'))
RS = {v: json.load(open(D + 'resel_%s.json' % v)) for v in VARS if os.path.exists(D + 'resel_%s.json' % v)}
# reproduction of the published grid at base
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
wd = lambda r: min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
b = RS['base']['compact']
repro = dict(n=len(b), max_abs_path_cagr=max(abs(b[i][0] - G[i]['dev250_path']['cagr']) for i in b), max_abs_wd=max(abs(b[i][1] - wd(G[i])) for i in b))
out = dict(id='costtax', data_end='2014-12-31', labels=dict(bond='synthetic 10y (and 7y rebuild) Treasury ETF total return from y10 = NON-ACTUAL reconstruction',
           fx='FRED DEXKOUS (ACTUAL, A10-1 quality gate FAIL -> stress version); path-KRW uses FX bootstrapped with the same blocks = NON-ACTUAL'),
           variants={v: dict(bond_halfyears=RS[v]['bond_halfyears'], engine_kw=RS[v]['engine_kw']) for v in RS}, base_reproduction=repro, picks={}, reselection={}, krw={})
for s in ('T25', 'T30', 'T40', 'T40_gatefix', 'hold1x_QQQ', 'v1_s085'):
    rows = {}
    base = PK['rows']['%s|base' % s]
    for v in VARS:
        r = PK['rows'].get('%s|%s' % (s, v))
        if not r: continue
        d = dict(path_cagr=r['dev250_path']['cagr'], path_mdd_p10=r['dev250_path']['mdd_p10'], ndx_cagr=r['real_ndx_86_14']['cagr'], ndx_mdd=r['real_ndx_86_14']['mdd'],
                 spx29_cagr=r['real_spx_29_54']['cagr'], spx29_mdd=r['real_spx_29_54']['mdd'], wd=r['wd'],
                 d_path_cagr_pp=100 * (r['dev250_path']['cagr'] - base['dev250_path']['cagr']), d_wd_pp=100 * (r['wd'] - base['wd']),
                 ndx_krw_cagr=r['real_ndx_86_14']['krw_cagr'], ndx_krw_mdd=r['real_ndx_86_14']['krw_mdd'],
                 path_krw_cagr_NONACTUAL=r['dev250_path']['krw_cagr'], path_krw_mdd_p10_NONACTUAL=r['dev250_path']['krw_mdd_p10'])
        if s in BUD: d['in_tier'] = bool(r['wd'] >= BUD[s])
        rows[v] = d
    e = dict(rows=rows)
    if s in BUD:
        mv = sorted(SINGLE, key=lambda v: rows[v]['d_path_cagr_pp'])
        e['largest_single_path_cagr_drop'] = (mv[0], rows[mv[0]]['d_path_cagr_pp'])
        e['largest_single_wd_drop'] = min(((v, rows[v]['d_wd_pp']) for v in SINGLE), key=lambda x: x[1])
        e['single_variants_out_of_tier'] = [v for v in SINGLE if not rows[v]['in_tier']]
        e['combos_out_of_tier'] = [v for v in ('combo_mid', 'combo_adv') if not rows[v]['in_tier']]
        e['krw_real_ndx_in_tier'] = bool(rows['base']['ndx_krw_mdd'] >= BUD[s])
        e['krw_ndx_dates'] = dict(usd_peak=PK['rows']['%s|base' % s]['real_ndx_86_14']['usd_mdd_peak'], usd_trough=PK['rows']['%s|base' % s]['real_ndx_86_14']['usd_mdd_trough'],
                                  krw_peak=PK['rows']['%s|base' % s]['real_ndx_86_14']['krw_mdd_peak'], krw_trough=PK['rows']['%s|base' % s]['real_ndx_86_14']['krw_mdd_trough'])
    out['picks'][s] = e
for v, R in RS.items():
    cp = R['compact']   # id -> [path_cagr, wd, ndx_cagr, path_mdd_p10, ndx_mdd, spx29_mdd]
    f = lambda i: None if i is None else dict(id=i, path_cagr=cp[i][0], wd=cp[i][1], ndx_cagr=cp[i][2], path_mdd_p10=cp[i][3], ndx_mdd=cp[i][4], spx29_mdd=cp[i][5])
    out['reselection'][v] = {t: dict(n_in=x['n_in'], union_best=f(x['union_best']), df1_best=f(x['df1_best']), adopted_gate_src=f(x.get('adopted_src')),
                                     adopted_gate_path=f(x.get('adopted_path')), gate=x.get('gate'), top5=x.get('top5'))
                             for t, x in R['tiers'].items()}
out['krw']['fx'] = PK['fx']
out['krw']['reselection'] = {k: dict(n_in=v['n_in'], union_best=v['union_best'], df1_best=v['df1_best'],
                                     union_row=v['union_row'], df1_path_cagr=(v['df1_row'] or {}).get('path_cagr')) for k, v in KR['tiers'].items() if '|path_cagr|' in k}
json.dump(out, open(D + 'result.json', 'w'), indent=1)
print(json.dumps(repro))
for s, e in out['picks'].items():
    print('==', s, {k: v for k, v in e.items() if k != 'rows'})
    for v, d in e['rows'].items():
        print('   %-10s path %.4f (%+.2fpp) p10mdd %.4f ndx %.4f/%.4f spx29 %.4f WD %.4f (%+.2fpp) %s | KRW ndx %.4f/%.4f path(NA) %.4f/%.4f' % (
            v, d['path_cagr'], d['d_path_cagr_pp'], d['path_mdd_p10'], d['ndx_cagr'], d['ndx_mdd'], d['spx29_mdd'], d['wd'], d['d_wd_pp'], d.get('in_tier', ''),
            d['ndx_krw_cagr'], d['ndx_krw_mdd'], d['path_krw_cagr_NONACTUAL'], d['path_krw_mdd_p10_NONACTUAL']))
for v, t in out['reselection'].items():
    print('RESEL %-9s' % v, ' | '.join('%s n%d src %s %.4f/%.4f path %s %.4f' % (k, x['n_in'], x['adopted_gate_src']['id'], x['adopted_gate_src']['path_cagr'], x['adopted_gate_src']['wd'],
          x['adopted_gate_path']['id'], x['adopted_gate_path']['path_cagr']) for k, x in t.items() if x['adopted_gate_src']))

# ---- verdicts (written after reading the numbers above; text only, numbers come from the rows)
out['verdict'] = {
 'T25': 'Headline 8.97% is cut most by account size (W0 300M: 8.04%, -0.93pp) and cost 0.45%/side (8.09%, -0.89pp). cost 0.45%/side pushes it OUT of the -25% tier '
        '(WD -25.67%, SPX29 leg); re-selection then gives v1|s0.1|L1.0|K1|RC at 4.43%. In KRW (DEXKOUS) its real-NDX MDD is -27.73% (USD -19.05%) -> out of tier in KRW terms. '
        '7y bond keeps it in tier but re-selection flips the tier pick to DF2|M2|b1|v1|s0.15|L1.0|K1|RB (10.79%, WD -24.90%).',
 'T30': 'Sits on the -30% boundary (WD -29.97%): 6 of 8 single realistic variants push it out (W0 30M/100M/300M, bond ER 0.25%, harvest off, cost 0.45%). '
        'Largest headline drop: cost 0.45% (10.18 -> 8.87%); W0 300M 9.17%. Re-selected tier headline then ranges 9.34%-11.75% with 4 different configs. '
        'KRW real-NDX MDD -32.40% (USD -21.02%) -> out of tier in KRW terms.',
 'T40': 'Stays in the -40% tier under every variant and both combos (worst WD -39.57% at cost 0.45%). Largest headline drop W0 300M (13.24 -> 12.40%). '
        'But its ADOPTION is fragile: the corrected bond-excess gate (gate_fix.py, select_df2_fixed.json) already rejects it at base (9.55% < 9.82%) -> v1|s0.3|L1.0|K2|RB 11.42%; '
        'with the original gate it is also rejected at W0 >= 30M and bond ER 0.25%. KRW real-NDX MDD -37.56% (in tier).',
 'refs': 'QQQ 1x hold moves <= 0.08pp in every variant (KRW real-NDX MDD -81.0% vs USD -83.0%). v1 15.18% -> 14.74% at W0 300M, 14.87% at cost 0.45%, 14.89% harvest off; '
         'KRW real-NDX MDD -65.7% vs USD -70.0%.',
 'krw_reselection': 'With only the real-NDX leg in KRW, the -25% tier is empty and the -30% tier pick becomes DF2|M0|b2|v1|s0.2|L1.0|K1|RB 10.85% (DF2 gate not applied; DF1 best '
                    'v1|s0.1|L3.0|K2|RB 9.31%). With bootstrapped FX on the paths too (NON-ACTUAL), only static QQQ30/bond survives any tier (-40%).'}
json.dump(out, open(D + 'result.json', 'w'), indent=1)
