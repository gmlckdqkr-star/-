import json, numpy as np
d = json.load(open('/mnt/project-files/research/df1/results/df3.json')); C = d['configs']
ids = list(C)
WD = {k: C[k]['WD'] for k in ids}; P0 = {k: C[k]['P0']['cagr'] for k in ids}; Pc = {k: C[k]['P']['cagr'] for k in ids}
WD0 = {k: min(C[k]['P0']['mdd_p10'], C[k]['N']['mdd'], C[k]['S']['mdd']) for k in ids}
def tier(th, wd=WD, key=P0):
    c = [k for k in ids if wd[k] >= th]; s = sorted(c, key=lambda k: -key[k]); return c, s
print('== S1 tiers: top 5 by P0, WD margins')
for th in (-0.25, -0.30, -0.40, -0.50, -0.60):
    c, s = tier(th); pk = d['sel']['S1']['%d' % (th*100)]['pick']
    print('tier %d n=%d pick %s P0 %.4f WD %.4f (margin %.2fpp)' % (th*100, len(c), pk, P0[pk], WD[pk], 100*(WD[pk]-th)))
    for k in s[:5]: print('    %-36s P0 %.4f P %.4f WD %.4f N %.4f' % (k, P0[k], Pc[k], WD[k], C[k]['N']['cagr']))
    n01 = sum(P0[s[0]] - P0[k] <= 0.001 for k in s); n025 = sum(P0[s[0]] - P0[k] <= 0.0025 for k in s)
    print('    within 0.10pp of top: %d, within 0.25pp: %d' % (n01, n025))
    # sensitivity of pick to threshold +-1pp
    for dth in (-0.01, 0.01):
        c2, s2 = tier(th + dth); print('    threshold %+.0fpp -> top %s P0 %.4f WD %.4f' % (dth*100, s2[0], P0[s2[0]], WD[s2[0]]))
print('== frontier (max P0) by WD tier, incl. looser tiers')
for th in (-0.25, -0.30, -0.35, -0.40, -0.45, -0.50, -0.55, -0.60, -0.65, -0.70, -0.75, -0.80, -0.85, -0.90, -1.0):
    c, s = tier(th); c0, s0 = tier(th, WD0)
    print('WD>=%d n=%4d top %-40s P0 %.4f (P %.4f, WD %.3f) | with bond-neutral WD0: n=%4d top %-38s P0 %.4f' % (th*100, len(c), s[0], P0[s[0]], Pc[s[0]], WD[s[0]], len(c0), s0[0] if s0 else '-', P0[s0[0]] if s0 else np.nan))
print('max P0 any config WD>=-0.60: %.4f ; QQQ hold P %.4f' % (max(P0[k] for k in ids if WD[k] >= -0.60), d['refs']['P']['hold1x_QQQ']['cagr']))
print('configs with P0 > QQQ hold:', sorted([(round(P0[k],4), round(WD[k],3), k) for k in ids if P0[k] > d['refs']['P']['hold1x_QQQ']['cagr']])[-8:], 'count', sum(P0[k] > d['refs']['P']['hold1x_QQQ']['cagr'] for k in ids))
# picks' WD under bond-neutral basis
for pk in ('v1|s0.1|L1.0|K1|RB','DF2|M0|b3|v1|s0.3|L1.0|K2|RB','DF3|N3|M2|v1|s0.2|L1.0|K0|RB','v1|s0.3|L1.0|K0|RB'):
    print('pick %-36s WD %.4f  WD0(bond-neutral path mdd_p10) %.4f  P0 mdd_p10 %.4f' % (pk, WD[pk], WD0[pk], C[pk]['P0']['mdd_p10']))
