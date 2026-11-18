import json
R = json.load(open('rebuild_raw.json')); C = R['cfg']; H = R['hold']; G = json.load(open('rebuild_gates.json'))
N = json.load(open('neighbours.json')); K = json.load(open('cmp_df4.json')); K3 = json.load(open('cmp_df3.json'))
rc = 'v1|s0.3|L1.5|K0|RC'; pc = lambda x: round(100 * x, 2)
S = dict(note='verify4/rebuild: independent DF4 screen from PRECOMMIT_DF4.md (df4.py/df4us.py/df4h.py not read). <=2014 data only. medians/percentiles only.',
  hold_refs={b: {k: pc(v) for k, v in h.items()} for b, h in H.items()}, bond_excess_applied=R['ex'],
  C1=dict(n_full_pass={k: v['n_full'] for k, v in G['variants'].items()}, n_us_and_R3={k: v['n_us_and_R3'] for k, v in G['variants'].items()},
          gate_pass_counts_R3strict=K['pass_counts_mine'], R3_pass_with_5pp_margin=1367 - G['variants']['exact|R3margin5']['fail_count']['R3'],
          sole_failing_gate_all10=G['variants']['exact|R3strict']['sole_failing_gate'], us_passers_R3=G['variants']['exact|R3strict']['us_R3'],
          near_miss_8gates=K['near_miss_mine']),
  C2=dict(us_pass=G['variants']['exact|R3strict']['us'], E4E5=G['variants']['exact|R3strict']['us_E4E5'],
          E4_cagr={i: pc(C[i]['E4|bx0']['cagr']) for i in G['variants']['exact|R3strict']['us']},
          E4_mddp10={i: pc(C[i]['E4|bx0']['mdd_p10']) for i in G['variants']['exact|R3strict']['us']},
          E5_cagr={i: pc(C[i]['E5|bx0']['cagr']) for i in G['variants']['exact|R3strict']['us']}),
  C3={k: {s: pc(v) for s, v in C[rc][k].items()} for k in ['dev250_path|bx0', 'E4|bx0', 'E5|bx0', 'cost3x|bx0', 'real_ndx_86_14|bx0', 'real_spx_55_85|bx0', 'real_spx_29_54|bx0', 'UK|bx0', 'CA|bx0', 'AU|bx0', 'DE|bx0', 'FR|bx0', 'JP|bx0']},
  C6=N, compare_df4=dict(value_maxabs=K['value_maxabs'], hold_maxabs=K['hold_maxabs'], gate_mismatch=K['gate_mismatch'], df4_us_stress=K['df4_us_stress'],
          us_pass_match=K['us_pass_df4us'] == K['us_pass_mine'], near_miss_match=[list(x) for x in K['near_miss_df4']] == [list(x) for x in K['near_miss_mine']]),
  compare_df3=K3)
json.dump(S, open('rebuild_summary.json', 'w'), indent=1)
print(json.dumps(S['C1'], indent=0)[:1500]); print(S['compare_df4']['us_pass_match'], S['compare_df4']['near_miss_match'])
