"""Merge the audit check outputs (scratch JSONs given as args) + the findings list into verify/audit/audit.json."""
import sys, json
d = sys.argv[1]
ev = {k: json.load(open('%s/%s.json' % (d, k))) for k in ('sel', 'eng', 'gate', 'misc', 'regrid', 'perpath')}
F = [
 dict(id='F1', severity='high', changes_pick=True,
      title='DF2 gate (a) bond-excess-0 shift uses the bootstrapped-path mean, not the source-period mean the pre-registration specifies; under the text the tier -40% DF2 pick fails gate (a)',
      evidence=dict(code='run_df2.py:34 ex = mean(mp.rb[:,W:] - mp.rf[:,W:]) on dev250_path; same in robust.py:16 / robust2.py:16',
                    text='PRECOMMIT_DF1 s5: rb minus the mean (rb - rf) of that basis\' raw-data period; PRECOMMIT_DF2 gate (a) uses that row',
                    ex_code_per_day=ev['gate']['D_ex']['ex_path_code'], ex_source_1986_2014_per_day=ev['gate']['D_ex']['ex_src'],
                    ex_real_ndx_basis_robust_json=1.3951832807568743e-04,
                    tierC_gate_a_code=[ev['gate']['D_gates']['C']['df2_bondx0_path'], ev['gate']['D_gates']['C']['df1_bondx0_path']],
                    tierC_gate_a_text=[ev['gate']['D_gates']['C']['df2_bondx0_src'], ev['gate']['D_gates']['C']['df1_bondx0_src']],
                    tierC_gate_a_perpath_reading=[ev['perpath']['C']['df2'], ev['perpath']['C']['df1']],
                    break_even_ex_per_day_approx=1.264e-04,
                    tierB_gate_a=dict(code=ev['gate']['D_gates']['B']['a_margin_path'], text=ev['gate']['D_gates']['B']['a_margin_src'])),
      impact='Per the literal text the tier -40% adopted pick is DF1 v1|s0.3|L1.0|K2|RB (path median 0.1142, WD -0.3478, V1 pass, V2 6/6, V3 median pct 76.9 in union set) instead of DF2|M2|b1|v1|s0.3|L1.5|K2|RB. Under the code reading the DF2 pass margin is +0.0175pp (per-path reading +0.032pp): not robust under any reading. Tier -30% unchanged (gate fails either way). dev250_path bondx0 rows in robust*.json remove 0.37%/yr less excess than specified.'),
 dict(id='F2', severity='medium', changes_pick=False,
      title='Tier -40% DF2 pick passes V2 with exactly 5/6: AU MDD -63.6% from one-day 3x gap (1987-10-20)',
      evidence=ev['misc']['AU_anatomy'], impact='Disclosure; M2 (TQQQ L/3 sleeve) has single-day gap exposure the 2-day-delayed knee cannot stop. Moot if F1 is applied (DF1 pick AU -33.9%).'),
 dict(id='F3', severity='low', changes_pick=False,
      title='Tier -30% pick sits inside the tier by 0.027pp (49/500 paths <= -30%)',
      evidence=ev['gate']['E_mdd_convention']['pick_detail']['v1|s0.2|L1.0|K1|RB'],
      impact='Robust to percentile definition and to MDD start-point convention; one more path crossing -30% would drop it (next: v1|s0.15|L1.0|K1|RB, path 0.0986). Disclosure only.'),
 dict(id='F4', severity='low', changes_pick=False,
      title='parity.json / units.json are narrow; units bond_final_diff 6.6e-4 is the test formula, not the engine; parity MDD diffs are the MDD start-point convention',
      evidence=dict(parity=ev['misc']['parity_mdd_convention'], units=ev['misc']['units_bond_final_diff'], independent_reference_engine=ev['eng']['C_reference_engine']),
      impact='No engine bug: an independent pure-python engine (QQQ/TQQQ/bond/T-bill, knee, ea rule, vmode 0/2, RBT, harvest, yearly static rebalance; base, cost 2x, delay 3, MS1 cash) matches dfe to <=8.2e-15 rel. on final wealth and <=2.7e-15 on MDD with identical trade counts, 4 bases x 10 configs x 4 variants.'),
 dict(id='F5', severity='low', changes_pick=False,
      title='Latent / reporting gaps in run_df2: gate skipped when tier name is A (line 46); no neighbour row for the DF2 pick; bondup not recomputed under bond-excess-0',
      evidence=dict(union_A_n_in=ev['sel']['selection']['UNION']['A']['n_in'], df2_pick_neighbours=ev['sel']['selection']['UNION']['C']['neighbors'],
                    df2_pick_neighbours_in_median=ev['sel']['selection']['UNION']['C']['neighbors_in_median'],
                    rebond_vs_not=dict(C=[ev['gate']['D_gates']['C']['df2_bondx0_src'], ev['gate']['D_gates']['C']['df2_bondx0_src_rebond']])),
      impact='No effect: union tier -20% is empty; both gate comparisons are RB (bondup unused).'),
 dict(id='F6', severity='none', changes_pick=False, title='No look-ahead / leakage; t+2 execution; cpn and bondup aligned; no post-2014 row',
      evidence=dict(data=ev['eng']['A_data'], causality={k: (v['signals_prefix_mismatch'] if 'frac' in k else v) for k, v in ev['eng']['B_causality'].items()})),
 dict(id='F7', severity='none', changes_pick=False, title='Grid sets, selection, tie rule, fallback, V1/V2/V3 reproduce exactly; DF1 grid reproduces with the post-edit engine',
      evidence=dict(grid=ev['sel']['grid'], regrid=ev['regrid'], main_tier=ev['sel']['main_tier'], gates_recorded=ev['sel']['gates_recorded'])),
]
json.dump(dict(auditor='audit', findings=F, evidence=ev), open('/mnt/project-files/research/df1/verify/audit/audit.json', 'w'), indent=1, default=str)
print('ok')
