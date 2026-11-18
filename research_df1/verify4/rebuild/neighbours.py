import json, sys
R = json.load(open('rebuild_raw.json')); C = R['cfg']; H = R['hold']; P = 'dev250_path'; MG = .05
def us(i):
    r = C[i]; n = r['real_ndx_86_14|bx0']; s = r['real_spx_55_85|bx0']; p = r[P + '|bx0']; z = r['real_spx_29_54|bx0']
    g = dict(R1=n['cagr'] > H['real_ndx_86_14']['cagr'] and n['mdd'] > H['real_ndx_86_14']['mdd'] + MG,
             R2=s['cagr'] > H['real_spx_55_85']['cagr'] and s['mdd'] > H['real_spx_55_85']['mdd'] + MG,
             V1=p['cagr'] > H[P]['cagr'], V2=p['mdd'] > H[P]['mdd'] + MG, E1=p['p10'] > H[P]['p10'], E2=p['mdd_p10'] > H[P]['mdd_p10'] + MG,
             E3=z['cagr'] > H['real_spx_29_54']['cagr'] and z['mdd'] > H['real_spx_29_54']['mdd'] + MG)
    return [k for k, v in g.items() if not v], dict(path=round(p['cagr']*100,2), p10=round(p['p10']*100,2), mdd=round(p['mdd']*100,1), mddp10=round(p['mdd_p10']*100,1),
             N=(round(n['cagr']*100,2), round(n['mdd']*100,1)), S55=(round(s['cagr']*100,2), round(s['mdd']*100,1)), S29=(round(z['cagr']*100,2), round(z['mdd']*100,1)))
out = {}
for ro in ('RC', 'RB', 'RT', 'RBT'):
    for s in ('snone', 's0.1', 's0.15', 's0.2', 's0.3', 's0.4'):
        for L in ('L1.0', 'L1.5', 'L2.0', 'L3.0'):
            i = 'v1|%s|%s|K0|%s' % (s, L, ro)
            if i not in C:
                j = 'DF3|N1|M0|v1|%s|%s|K0|%s' % (s, L, ro)
                if j in C: i = j
                else: continue
            if s in ('s0.2', 's0.3', 's0.4') and L in ('L1.0', 'L1.5', 'L2.0'):
                f, v = us(i); out[i] = dict(fails=f, vals=v); print('%-32s fails=%-22s %s' % (i, f, v))
for i in ['v1|s0.3|L1.5|K1|RC', 'v1|s0.3|L1.5|K2|RC', 'always|s0.3|L1.5|K0|RC']:
    f, v = us(i); out[i] = dict(fails=f, vals=v); print('%-32s fails=%-22s %s' % (i, f, v))
json.dump(out, open('neighbours.json', 'w'), indent=1)
