import json, sys
sys.path.insert(0, '/tmp/df7v_repro'); import mygates as MG
OUT = '/mnt/project-files/research/df1/verify7/repro/'; RES = '/mnt/project-files/research/df1/results/'
S = {w: json.load(open(OUT + 's2_%s.json' % w)) for w in ('REAL', 'P', 'X')}
DM = json.load(open(RES + 'df7_main.json')); DF = json.load(open(RES + 'df7_final.json'))
Q = {}
for w in S:
    for k, v in S[w]['qqq']['PRIM'].items(): Q[k] = v['mine']
res = dict(qqq=Q)
# 1. fully re-run rules (all five keys present) -> gates from my re-run numbers
full = [i for i in S['P']['prim'] if i in S['X']['prim'] and i in S['REAL']['prim']]
rer = {}
for i in full:
    r = {}
    for w in S: r.update({k: v['mine'] for k, v in S[w]['prim'][i].items()})
    g = MG.gate(r, Q); rer[i] = dict(npass=sum(v['ok'] for v in g.values()), g={k: v['ok'] for k, v in g.items()},
                                   fail={k: v['fail'] for k, v in g.items() if not v['ok']}, stored_npass=DM['gates'][i]['npass'],
                                   same=all(DM['gates'][i]['g'][k] == g[k]['ok'] for k in g))
res['rerun_gates'] = rer
print('rules fully re-run (5 keys):', len(full), ' all-5 pass among them:', sum(v['npass'] == 5 for v in rer.values()),
      ' gate disagreements vs stored:', [i for i, v in rer.items() if not v['same']])
# max deviations over all re-run rows
mx = {}; bad = []
for w in S:
    for i, kk in S[w]['prim'].items():
        for k, v in kk.items():
            for f, d in v['d'].items():
                mx[f] = max(mx.get(f, 0), abs(d))
                if abs(d) > 1e-6 and f in ('cagr', 'p10', 'mdd_med', 'mdd_p10', 'pair'): bad.append((i, k, f, d))
print('PRIM rows: max|diff| per field', {f: '%.1e' % v for f, v in mx.items()}, ' >1e-6:', bad)
res['prim_maxdiff'] = mx; res['prim_bad'] = bad
res['n_rows'] = {w: len(S[w]['prim']) for w in S}
# 2. f* spot checks
fs = {}
for i in S['REAL']['fstar']:
    for f in S['REAL']['fstar'][i]:
        r = {}
        for w in S: r.update(S[w]['fstar'][i][f])
        g = MG.gate(r, Q); ok = all(v['ok'] for v in g.values())
        fs.setdefault(i, {})[f] = dict(ok=ok, stored=DF['fstar'][i]['ok'][f], fail={k: v['fail'] for k, v in g.items() if not v['ok']},
                                        G5=dict(p10=g['G5']['p10'], ddm=g['G5']['ddm']), G4=dict(pair=g['G4']['pair'], med=g['G4']['med']),
                                        meta={w: S[w]['panel_meta'][f]['trend_mean_ann'] / S[w]['panel_meta'][f]['trend_mean_ann_proxy'] for w in S})
        print('fstar', i, f, 'mine ok', ok, 'stored ok', DF['fstar'][i]['ok'][f], fs[i][f]['fail'], 'G5', fs[i][f]['G5'], 'trend frac realized', fs[i][f]['meta'])
res['fstar'] = fs
# 3. report rows
rep = {}
for conv in ('RAW', 'ZERO'):
    for w in ('REAL', 'X'):
        R = S[w]['report'][conv]
        for k, v in R['qqq'].items(): rep.setdefault(conv, {})['QQQ_' + k] = max(abs(x) for x in v['d'].values())
        for i, kk in R['rows'].items():
            for k, v in kk.items(): rep[conv][i + '_' + k] = max(abs(x) for x in v['d'].values())
print('report max|diff|', json.dumps(rep, indent=0))
res['report_maxdiff'] = rep
res['panel_meta'] = {w: {c: S[w]['panel_meta'][c] for c in S[w]['panel_meta']} for w in S}
res['sig_check'] = {w: S[w]['sig_check'] for w in S}
res['qqq_parity'] = {w: {c: {k: (v['dfk_parity_cg'], v['dfk_parity_md'], max(abs(x) for x in v['d_stored'].values())) for k, v in q.items()} for c, q in S[w]['qqq'].items()} for w in S}
print('qqq parity / stored diff', res['qqq_parity']); print('sig', res['sig_check'])
json.dump(res, open(OUT + 'repro_df7.json', 'w'), indent=1)
