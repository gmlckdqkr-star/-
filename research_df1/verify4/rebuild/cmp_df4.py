import json, numpy as np
RES = '/mnt/project-files/research/df1/results/'
R = json.load(open('rebuild_raw.json')); C = R['cfg']; H = R['hold']
G = json.load(open('rebuild_gates.json'))
D = json.load(open(RES + 'df4.json')); U = json.load(open(RES + 'df4_us.json'))
out = dict(value_maxabs={}, hold_maxabs={}, gate_mismatch={}, ex_diff={})
pairs = [('P0', 'dev250_path|bx0'), ('P', 'dev250_path|std')]
for b in ['real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP']:
    pairs += [(b + '_bx0', b + '|bx0'), (b, b + '|std')]
for dk, mk in pairs:
    mx = 0.0
    for i in C:
        for st in C[i][mk]: mx = max(mx, abs(D['configs'][i][dk][st] - C[i][mk][st]))
    out['value_maxabs'][dk] = mx
for b in H:
    out['hold_maxabs'][b] = max(abs(D['refs'][b]['hold1x_QQQ'][st] - H[b][st]) for st in H[b])
for b, e in R['ex'].items():
    if b in D['bond_excess']:
        theirs = D['bond_excess'][b]; out['ex_diff'][b] = dict(mine_applied=e, df4_raw=theirs, df4_applied=max(theirs, 0.0))
# gate-by-gate agreement (R3 strict = no margin, as df4 gate_counts imply)
V = G['variants']['exact|R3strict']
import importlib.util, sys
sys.argv = ['x']
exec(open('gates.py').read().split('EXACT =')[0].replace("RAW = sys.argv[1]; OUT = sys.argv[2]", "RAW='rebuild_raw.json'; OUT=None"))
EX = G['thresholds_exact']
mism = {}
for i in C:
    g = gates(i, EX, 0.0)
    for k in ['R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3']:
        if bool(g[k]) != bool(D['configs'][i]['g'][k]): mism.setdefault(k, []).append(i)
    if g['R3_n'] != D['configs'][i]['g']['R3n']: mism.setdefault('R3n', []).append(i)
    nf = sum(not g[k] for k in ['R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3'])
    if nf != D['configs'][i]['nfail']: mism.setdefault('nfail', []).append(i)
out['gate_mismatch'] = {k: len(v) for k, v in mism.items()}; out['gate_mismatch_examples'] = {k: v[:5] for k, v in mism.items()}
mycounts = {k: int(sum(gates(i, EX, 0.0)[k] for i in C)) for k in ['R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3']}
out['pass_counts_mine'] = mycounts; out['pass_counts_df4'] = D['gate_counts']
# near-miss list (8 gates)
nf8 = {i: [k for k in ['R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3'] if not gates(i, EX, 0.0)[k]] for i in C}
nm = sorted(C, key=lambda i: (len(nf8[i]), -C[i]['dev250_path|bx0']['cagr']))[:10]
out['near_miss_mine'] = [(i, nf8[i]) for i in nm]; out['near_miss_df4'] = D['sel']['near_miss']
out['n_pass_df4'] = D['n_pass']; out['n_pre_df4'] = D['n_pre']
# df4_us stress
sm = {}
for i, s in U['stress'].items():
    sm[i] = dict(c2_vs_E4=max(abs(s['c2'][k] - C[i]['E4|bx0'][k]) for k in s['c2']),
                 d4_vs_E5=max(abs(s['d4'][k] - C[i]['E5|bx0'][k]) for k in s['d4']),
                 c3_vs_cost3x=max(abs(s['c3'][k] - C[i]['cost3x|bx0'][k]) for k in s['c3']),
                 E4_df4us=s['E4'], E4_mine=V['us_E4E5'][i]['E4'], E5_df4us=s['E5'], E5_mine=V['us_E4E5'][i]['E5'])
out['df4_us_stress'] = sm; out['us_pass_df4us'] = sorted(U['us_pass']); out['us_pass_mine'] = V['us']
json.dump(out, open('cmp_df4.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
