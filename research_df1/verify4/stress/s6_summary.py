"""verify4/stress: collect s1..s5 numbers into stress_summary.json (percent units, medians/percentiles only)."""
import json
P = '/mnt/project-files/research/df1/verify4/stress/'
s1 = json.load(open(P + 's1_main.json'))['rows']; s2 = json.load(open(P + 's2_boot.json'))['rows']; s3 = json.load(open(P + 's3_halves.json'))['rows']
s4 = json.load(open(P + 's4_seedscan.json'))['summary']; s5 = json.load(open(P + 's5_boot_e4e5.json'))
pc = lambda d: {k: round(v * 100, 2) for k, v in d.items() if isinstance(v, float) and k != 'loss_share'}
S = dict(config='v1|s0.3|L1.5|K0|RC', comparator='QQQ hold (dfe.run L=1) under the same change; RC and QQQ hold use no bond -> bond-neutral irrelevant',
         a_path={k.split('|')[1]: dict(cand=pc(v['cand']), qqq=pc(v['qqq']), beats_both=v['beats_both']) for k, v in s1.items() if k.startswith('path|')},
         single={k: dict(cand=pc(v['cand']), qqq=pc(v['qqq']), beats_both=v['beats_both']) for k, v in s1.items() if not k.startswith('path|') and not k.endswith('window')},
         single_sep={k: dict(cand=pc(v['cand']), qqq=pc(v['qqq']), beats_both=v['beats_both']) for k, v in s3.items() if '|' in k},
         b_halves={k: dict(window=v['window'], A=dict(cand=pc(v['A_standalone']['cand']), qqq=pc(v['A_standalone']['qqq']), beats_both=v['A_standalone']['beats_both']),
                           B=dict(cand=pc({x: y for x, y in v['B_continuous']['cand'].items() if x != 'days'}), qqq=pc({x: y for x, y in v['B_continuous']['qqq'].items() if x != 'days'}),
                                  beats_both=v['B_continuous']['beats_both'])) for k, v in s3.items() if '|' not in k},
         e_boot={k: dict(cand=pc(v['cand']), qqq=pc(v['qqq']), beats_both=v['beats_both'], gates=v['gate_like']) for k, v in s2.items()},
         e_seedscan=s4,
         e_boot_stress={k: {kk: (dict(cand=pc(vv['cand']), qqq_same=pc(vv['qqq_same']), gate_vs_base=vv['gate_vs_base'], beats_same_both=vv['beats_same_both'])
                                 if kk != 'qqq_base' else pc(vv)) for kk, vv in v.items()} for k, v in s5.items()},
         f_krw='not run: robust2.py (and every file in df1/code) has no DEXKOUS/KRW conversion stress; nothing to rerun')
json.dump(S, open(P + 'stress_summary.json', 'w'), indent=1); print('saved', len(json.dumps(S)))
