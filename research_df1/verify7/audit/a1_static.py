"""DF7 audit step 1: configs(), df7_main.json / df7_final.json consistency (no world loads). <=2014 results only."""
import sys, json, re, hashlib
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D, df5gate as GT
RES = '/mnt/project-files/research/df1/results/'
out = {}
# ---- lock
lk = open('/mnt/project-files/research/df1/PRECOMMIT_DF7.sha256').read().split()
sh = {p: hashlib.sha256(open('/mnt/project-files/research/df1/' + p, 'rb').read()).hexdigest() for p in ('PRECOMMIT_DF7.md', 'code/df7.py')}
out['lock'] = dict(file=lk, actual=sh, ok=(sh['PRECOMMIT_DF7.md'] == lk[0] and sh['code/df7.py'] == lk[2]))
# ---- configs
C = D.configs(); fam = {}
for c in C: fam[c['fam']] = fam.get(c['fam'], 0) + 1
bad = []
for c in C:
    if c['fam'] in ('F1', 'F2'):
        w = c['w']; s = sum(w.values())
        if abs(s - 1) > 1e-9 or min(w.values()) < 0: bad.append((c['id'], 'sum/neg', s))
        m = re.match(r'(F[12])\|q([\d.]+)\|(g|r)([\d.]+)\|(t|g)([\d.]+)\|m([\d.]+)$', c['id'])
        if c['fam'] == 'F1':
            exp = dict(QLD=float(m.group(2)), GOLD=float(m.group(4)), LTT=float(m.group(6)), DBMF=float(m.group(7)))
        else:
            exp = dict(QLD=float(m.group(2)), RSST=float(m.group(4)), GDE=float(m.group(6)), DBMF=float(m.group(7)))
        if any(abs(exp[k] - w[k]) > 1e-9 for k in exp) or set(exp) != set(w): bad.append((c['id'], 'id-mismatch', w))
        if c['fam'] == 'F1' and not (w['QLD'] in (.2, .3, .4, .5, .6) and w['GOLD'] in (0, .1, .2, .3) and w['LTT'] in (0, .1, .2, .3)): bad.append((c['id'], 'grid'))
        if c['fam'] == 'F2' and not (w['QLD'] in (.2, .3, .4, .5) and round(w['RSST'] * 10) == w['RSST'] * 10 and w['RSST'] <= .8 + 1e-9 and w['GDE'] <= .4 + 1e-9): bad.append((c['id'], 'grid'))
    else:
        for k in ('on', 'off'):
            s = sum(c[k].values())
            if abs(s - 1) > 1e-9 or min(c[k].values()) < 0: bad.append((c['id'], k, s))
ids = [c['id'] for c in C]
out['configs'] = dict(n=len(C), fam=fam, unique=len(set(ids)) == len(ids), bad=bad,
                      P2=[c for c in C if c['id'] == 'F2|q0.3|r0.2|g0.3|m0.2'],
                      F3=[(c['id'], c['on'], c['off']) for c in C if c['fam'] == 'F3'],
                      min_w=min(min(c['w'].values()) for c in C if 'w' in c))
# ---- main json
M = json.load(open(RES + 'df7_main.json'))
out['main_meta'] = M['meta']
out['main_configs_equal'] = (M['configs'] == json.loads(json.dumps(C)))
G2 = D.gates(M['rows'], M['qqq'])
diff = [i for i in G2 if (G2[i]['npass'], round(G2[i]['score'], 12), round(G2[i]['ddm'], 12), G2[i]['g']) != (M['gates'][i]['npass'], round(M['gates'][i]['score'], 12), round(M['gates'][i]['ddm'], 12), M['gates'][i]['g'])]
out['main_gates_recomputed_diff'] = diff
famof = {c['id']: c['fam'] for c in C}
out['main_counts'] = {f: dict(n=sum(famof[i] == f for i in G2), pass5=sum(famof[i] == f and G2[i]['npass'] == 5 for i in G2),
                             each={k: sum(famof[i] == f and G2[i]['g'][k] for i in G2) for k in ('G1', 'G2', 'G3', 'G4', 'G5')},
                             npass_hist={n: sum(famof[i] == f and G2[i]['npass'] == n for i in G2) for n in range(6)}) for f in ('F1', 'F2', 'F3')}
out['main_keys'] = sorted(set(k for r in M['rows'].values() for k in r))
out['qqq_main'] = M['qqq']
# ---- final json
F = json.load(open(RES + 'df7_final.json'))
out['final_keys'] = list(F.keys())
out['final_meta'] = F['meta']; out['final_gpass'] = F['gpass']; out['final_H'] = F['H']; out['final_select'] = F['select']; out['final_counts'] = F['counts']
out['final_best'] = F['best']
# recompute best per family
best = {}
for c in C:
    k = c['fam']; g = G2[c['id']]
    if k not in best or (g['npass'], g['score']) > (G2[best[k]]['npass'], G2[best[k]]['score']): best[k] = c['id']
out['best_recomputed'] = best; out['best_match'] = best == F['best']
out['best_detail'] = {f: dict(id=i, npass=G2[i]['npass'], score=G2[i]['score'], ddm=G2[i]['ddm'], fail=G2[i]['fail']) for f, i in best.items()}
out['report_ids'] = F.get('report_ids')
out['fstar'] = F.get('fstar')
# f* at 0.5 must equal main pass flag
fs = F.get('fstar') or {}
out['fstar_vs_main_at_0.5'] = {i: dict(fstar_ok05=v['ok'].get('0.5'), main_pass=G2[i]['npass'] == 5) for i, v in fs.items()}
# report structure
rep = F.get('report', {})
out['report_struct'] = {cv: dict(ids=sorted(rep[cv]['rows'].keys()), keys=sorted(set(k for r in rep[cv]['rows'].values() for k in r)), qqq_keys=sorted(rep[cv]['qqq'].keys())) for cv in rep}
# PRIM report rows vs main rows on the shared keys (REAL, P30, P10, X30, X10)
mm = []
for i in rep.get('PRIM', {}).get('rows', {}):
    if i not in M['rows']: continue
    for k in ('REAL', 'P30', 'P10', 'X30', 'X10'):
        a = rep['PRIM']['rows'][i].get(k); b = M['rows'][i].get(k)
        if a is None or b is None: continue
        d = max(abs(a[x] - b[x]) for x in ('cagr', 'p10', 'mdd_med', 'mdd_p10', 'pair'))
        mm.append((i, k, d))
out['report_PRIM_vs_main_maxdiff'] = max([x[2] for x in mm]) if mm else None
# step A consistency: P2 / P3 RAW and ZERO vs df7_user.json
U = json.load(open(RES + 'df7_user.json'))
um = {'F2|q0.3|r0.2|g0.3|m0.2': 'P2 QLD30/GDE30/RSST20/DBMF20', 'U|P3': 'P3 QLD35/GDE30/RSST20/DBMF15'}
cmp = {}
for cv in ('RAW', 'ZERO'):
    for rid, un in um.items():
        rr = rep.get(cv, {}).get('rows', {}).get(rid, {})
        for k, v in rr.items():
            uk = k + '_' + cv
            if uk in U['rows'][un]:
                u = U['rows'][un][uk]
                cmp['%s|%s|%s' % (cv, rid, k)] = max(abs(v[x] - u[x]) for x in ('cagr', 'p10', 'mdd_med', 'mdd_p10', 'pair'))
out['stepA_vs_report_maxdiff'] = cmp
json.dump(out, open('/tmp/df7v_audit/a1_out.json', 'w'), indent=1, default=str)
print(json.dumps({k: out[k] for k in ('lock', 'main_meta', 'main_configs_equal', 'main_gates_recomputed_diff', 'final_keys', 'final_meta', 'final_gpass', 'final_select', 'final_counts', 'best_match', 'report_ids', 'report_PRIM_vs_main_maxdiff')}, indent=1, default=str))
print(json.dumps(out['configs'], default=str)[:3000])
print(json.dumps(out['main_counts'], indent=0))
print(json.dumps(out['best_detail'], indent=0, default=str))
print(json.dumps(out['fstar_vs_main_at_0.5'], indent=0))
print(json.dumps(out['report_struct'], indent=0))
print(json.dumps(out['stepA_vs_report_maxdiff'], indent=0))
