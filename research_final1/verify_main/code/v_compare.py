"""Compare the verifier's results with the main session's result files (reads JSON only)."""
import json, sys
M = '/mnt/project-files/research/final1/results/'; V = '/mnt/project-files/research/final1/verify_main/results/'
ms = json.load(open(M + 'stack.json')); mn = json.load(open(M + 'nbr.json')); mm = json.load(open(M + 'mega.json'))
vs = json.load(open(V + 'v_stack.json')); vo = json.load(open(V + 'v_openfill.json')); vn = json.load(open(V + 'v_nbr.json'))
vm = json.load(open(V + 'v_mega.json')); vr = json.load(open(V + 'v_replay.json'))
BASES = ('real_ndx_86_14', 'dev250_glued', 'dev250_path', 'real_spx_55_85', 'real_spx_70_85')
out = {}; worst = {}
def upd(lane, key, a, b, scale=100.0):
    d = abs(a - b) * scale
    if d > worst.get(lane, (0, ''))[0] or lane not in worst: worst[lane] = (d, key)
# STACK S0-S5, S8 (measure2) and S6/S7 (OV1-B engine)
for nm in ('S0_base', 'S1_CASH0', 'S2_CASHRP', 'S3_FEE', 'S4_CASHRP_FEE', 'S5_CASH0_FEE', 'S8_delay1_CASHRP_FEE'):
    for b in BASES:
        for f in ('cagr', 'd_vs_s085', 'pw_vs_s085', 'mdd') + (('dd80', 'p10') if 'dev250' in b else ()):
            upd('STACK_S0-S5,S8' if f in ('cagr', 'd_vs_s085') else 'STACK_other_fields', '%s|%s|%s' % (nm, b, f), ms[nm][b][f], vs[nm][b][f])
for nm in ('S6_OPENFILL', 'S6x_OPENFILL_xcost0.1', 'S7_OPENFILL_CASHRP_FEE', 'S7x_OPENFILL_CASHRP_FEE_xcost0.1'):
    for b in BASES:
        for f in ('cagr', 'd_vs_s085', 'pw_vs_s085'):
            upd('STACK_S6-S7x', '%s|%s|%s' % (nm, b, f), ms[nm][b][f], vo[nm][b][f])
for h in ('1999_2007', '2008_2014'):
    upd('STACK_halves_S(abs units)', h, ms['OPENFILL_rule']['halves'][h]['S'], vo['halves'][h]['S_weighted_all'], 1.0)
    assert ms['OPENFILL_rule']['halves'][h]['n_events'] == vo['halves'][h]['n_events']
assert ms['OPENFILL_rule']['adopt'] == vo['adoption_rule']['adopt'] == False
# pure-python replay vs main (single-path bases)
for nm in vr['stack_replay']:
    for b in vr['stack_replay'][nm]:
        upd('STACK_replay_vs_main', '%s|%s' % (nm, b), ms[nm][b]['cagr'], vr['stack_replay'][nm][b]['cagr'])
for nm in ('NBR5', 'NBR9'):
    for b in vr['nbr_joint_book'][nm]:
        upd('NBR_replay_vs_main', '%s|%s' % (nm, b), mn[nm + '|base'][b]['cagr'], vr['nbr_joint_book'][nm][b]['own_books'])
# NBR
for k in ('NBR5|base', 'NBR9|base', 'NBR5|delay3', 'NBR9|delay3', 'NBR5|cost2x', 'NBR9|cost2x'):
    for b in BASES:
        for f in ('cagr', 'd_vs_v1', 'pw_vs_v1', 'mdd', 'v1') + (('dd80', 'p10') if 'dev250' in b else ()):
            upd('NBR_' + ('base' if k.endswith('base') else 'stress') + ('' if f in ('cagr', 'd_vs_v1') else '_other_fields'), '%s|%s|%s' % (k, b, f), mn[k][b][f], vn[k][b][f])
        for p, x in mn[k][b]['sub_cagr'].items(): upd('NBR_sub_accounts', '%s|%s|%s' % (k, b, p), x, vn[k][b]['sub_cagr'][p])
assert mn['PASS'] == vn['PASS']
# MEGA
for col in ('Hi 10', 'Hi 20', 'Lo 10'):
    for w in ('1963_2014', 'half1_1963_1988', 'half2_1989_2014', '1986_2014', '1926_2014', '1986_1999', '2000_2014'):
        upd('MEGA_ann_diff_pp', '%s|%s' % (col, w), mm[col][w]['ann_diff_pp'], vm[col][w]['ann_diff_pp'], 1.0)
        upd('MEGA_t', '%s|%s' % (col, w), mm[col][w]['t'], vm[col][w]['t'], 1.0)
        upd('MEGA_cagr', '%s|%s' % (col, w), mm[col][w]['cagr_port'], vm[col][w]['cagr_port']); upd('MEGA_cagr', '%s|%s|mkt' % (col, w), mm[col][w]['cagr_mkt'], vm[col][w]['cagr_mkt'])
        assert mm[col][w]['n_months'] == vm[col][w]['n_months']
for col in ('Hi 10', 'Hi 20'): assert mm[col]['PASS'] == vm[col]['PASS'] == False
assert mm['source']['sha_me'] == vm['source']['sha_me'] and mm['source']['sha_ff'] == vm['source']['sha_ff']
for k, (d, key) in worst.items(): print('%-28s max abs diff %.3e  (%s)' % (k, d, key))
json.dump({k: dict(max_abs_diff=d, at=key) for k, (d, key) in worst.items()}, open(V + 'v_compare.json', 'w'), indent=1)
