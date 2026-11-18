"""pack intermediate outputs into the single repro_df7.json and remove the intermediates"""
import json, os
OUT = '/mnt/project-files/research/df1/verify7/repro/'
R = json.load(open(OUT + 'repro_df7.json')); S1 = json.load(open(OUT + 's1_gates_stored.json'))
S = {w: json.load(open(OUT + 's2_%s.json' % w)) for w in ('REAL', 'P', 'X')}
R['stored_rows_gate_recompute'] = dict(n=S1['n'], all5=S1['all5'], mismatches_vs_stored=S1['mism'], borderline_lt_1e6=S1['border'], best=S1['best'],
                                      per_rule={i: dict(npass=v['npass'], fail=v['fail']) for i, v in S1['res'].items()})
R['cfg_check'] = S['REAL']['cfg_check']; R['real_dates'] = S['REAL']['real_dates']
R['rerun_rows_PRIM'] = {i: {k: v['mine'] for w in S for k, v in S[w]['prim'][i].items()} for i in S['REAL']['prim']}
R['fstar_rows'] = {i: {f: {k: v for w in S for k, v in S[w]['fstar'][i][f].items()} for f in S['REAL']['fstar'][i]} for i in S['REAL']['fstar']}
R['report_rows'] = {conv: {i: {k: v['mine'] for w in ('REAL', 'X') for k, v in S[w]['report'][conv]['rows'][i].items()} for i in S['REAL']['report'][conv]['rows']} for conv in ('RAW', 'ZERO')}
R['notes'] = 'All comparisons are mine - stored; tolerance 1e-6; produced by s1..s5 in this folder (python from /tmp/df7v_repro).'
json.dump(R, open(OUT + 'repro_df7.json', 'w'), indent=1)
for f in ['s1_gates_stored.json'] + ['s2_%s.json' % w for w in S]: os.remove(OUT + f)
print('packed', os.path.getsize(OUT + 'repro_df7.json'))
