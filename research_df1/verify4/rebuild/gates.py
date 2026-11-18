"""verify4/rebuild: gate evaluation from rebuild_raw.json (PRECOMMIT_DF4.md section 2, own code)."""
import sys, json, numpy as np
RAW = sys.argv[1]; OUT = sys.argv[2]
R = json.load(open(RAW)); H = R['hold']; C = R['cfg']
FOR = ['UK', 'CA', 'AU', 'DE', 'FR', 'JP']; MG = 0.05
P = 'dev250_path'
def gates(i, thr, r3margin):
    r = C[i]; g = {}
    n = r['real_ndx_86_14|bx0']; g['R1'] = n['cagr'] > thr['R1c'] and n['mdd'] > thr['R1m']
    s = r['real_spx_55_85|bx0']; g['R2'] = s['cagr'] > thr['R2c'] and s['mdd'] > thr['R2m']
    wins = [f for f in FOR if r[f + '|bx0']['cagr'] > H[f]['cagr'] and r[f + '|bx0']['mdd'] > H[f]['mdd'] + r3margin]
    g['R3'] = len(wins) >= 4; g['R3_n'] = len(wins)
    g['R3_cagr_n'] = sum(r[f + '|bx0']['cagr'] > H[f]['cagr'] for f in FOR)
    g['R3_mdd_n'] = sum(r[f + '|bx0']['mdd'] > H[f]['mdd'] + r3margin for f in FOR)
    p = r[P + '|bx0']
    g['V1'] = p['cagr'] > thr['V1']; g['V2'] = p['mdd'] > thr['V2']
    g['E1'] = p['p10'] > thr['E1']; g['E2'] = p['mdd_p10'] > thr['E2']
    z = r['real_spx_29_54|bx0']; g['E3'] = z['cagr'] > thr['E3c'] and z['mdd'] > thr['E3m']
    e4 = r['E4|bx0']; g['E4'] = e4['cagr'] > thr['V1'] and e4['mdd_p10'] > thr['E2']
    e5 = r['E5|bx0']; g['E5'] = e5['cagr'] > thr['V1'] and e5['mdd_p10'] > thr['E2']
    return g
EXACT = dict(R1c=H['real_ndx_86_14']['cagr'], R1m=H['real_ndx_86_14']['mdd'] + MG, R2c=H['real_spx_55_85']['cagr'], R2m=H['real_spx_55_85']['mdd'] + MG,
             V1=H[P]['cagr'], V2=H[P]['mdd'] + MG, E1=H[P]['p10'], E2=H[P]['mdd_p10'] + MG,
             E3c=H['real_spx_29_54']['cagr'], E3m=H['real_spx_29_54']['mdd'] + MG)
ROUND = dict(R1c=.1166, R1m=-.7799, R2c=.0900, R2m=-.4023, V1=.1172, V2=-.628, E1=.0559, E2=-.8001, E3c=.0643, E3m=-.7870)
US = ['R1', 'R2', 'V1', 'V2', 'E1', 'E2', 'E3']; ALL = US + ['R3', 'E4', 'E5']
res = dict(thresholds_exact=EXACT, thresholds_rounded=ROUND, hold=H, ex=R['ex'], variants={})
for tn, thr in (('exact', EXACT), ('rounded', ROUND)):
    for r3n, r3m in (('R3strict', 0.0), ('R3margin5', MG)):
        G = {i: gates(i, thr, r3m) for i in C}
        us = sorted(i for i in G if all(G[i][k] for k in US))
        full = sorted(i for i in G if all(G[i][k] for k in ALL))
        fail_cnt = {k: int(sum(not G[i][k] for i in G)) for k in ALL}
        only_fail = {k: int(sum((not G[i][k]) and all(G[i][j] for j in ALL if j != k) for i in G)) for k in ALL}
        nf = {i: sum(not G[i][k] for k in ALL) for i in G}
        best_fail = min(nf.values()); closest = sorted(i for i in G if nf[i] == best_fail)
        res['variants'][tn + '|' + r3n] = dict(n_us=len(us), us=us, us_E4E5={i: dict(E4=G[i]['E4'], E5=G[i]['E5']) for i in us},
            n_full=len(full), full=full, fail_count=fail_cnt, sole_failing_gate=only_fail,
            n_us_and_R3=int(sum(all(G[i][k] for k in US + ['R3']) for i in G)),
            closest_nfail=best_fail, closest=[(i, [k for k in ALL if not G[i][k]], G[i]['R3_n'], G[i]['R3_cagr_n'], G[i]['R3_mdd_n']) for i in closest[:20]],
            us_R3=[(i, G[i]['R3_n'], G[i]['R3_cagr_n'], G[i]['R3_mdd_n']) for i in us],
            max_R3_n_among_us=max([G[i]['R3_n'] for i in us], default=None),
            gates={i: G[i] for i in (us + closest[:20])})
        print(tn, r3n, 'US', len(us), us, 'FULL', len(full), 'closest', best_fail, len(closest))
json.dump(res, open(OUT, 'w'), indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else int(o))
