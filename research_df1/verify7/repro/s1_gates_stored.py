import sys, json
sys.path.insert(0, '/tmp/df7v_repro'); import mygates as MG
RES = '/mnt/project-files/research/df1/results/'
D = json.load(open(RES + 'df7_main.json')); Q = D['qqq']; rows = D['rows']; G0 = D['gates']; C = D['configs']
assert len(C) == 198 and len(rows) == 198
fams = {}
for c in C: fams.setdefault(c['fam'], []).append(c['id'])
print('families', {k: len(v) for k, v in fams.items()})
res = {}; mism = []; border = []
for c in C:
    i = c['id']; g = MG.gate(rows[i], Q); g12 = MG.gate(rows[i], Q, eps=1e-12)
    npass = sum(v['ok'] for v in g.values()); npass12 = sum(v['ok'] for v in g12.values())
    res[i] = dict(npass=npass, g={k: v['ok'] for k, v in g.items()}, fail={k: v['fail'] for k, v in g.items() if not v['ok']}, minmargin=MG.margins_min(g))
    st = G0[i]
    if st['npass'] != npass or any(st['g'][k] != g[k]['ok'] for k in g) or npass12 != npass:
        mism.append((i, st['npass'], npass, npass12, st['g'], res[i]['g']))
    # stored fail lists for G2..G5
    for k in ('G2', 'G3', 'G4', 'G5'):
        if not g[k]['ok'] and sorted(st['fail'].get(k) or []) != sorted(g[k]['fail']):
            mism.append((i, k, 'faillist', st['fail'].get(k), g[k]['fail']))
    if MG.margins_min(g) < 1e-6: border.append((i, MG.margins_min(g)))
    # score / ddm recomputation
    sc = min(rows[i]['P30']['pair'], rows[i]['X30']['pair'], rows[i]['REAL']['cagr'] - Q['REAL']['cagr'])
    ddm = min(g['G1']['ddm'], g['G2']['ddm'], g['G3']['ddm'], g['G4']['ddm'], g['G5']['ddm'])
    if abs(sc - st['score']) > 1e-12 or abs(ddm - st['ddm']) > 1e-12: mism.append((i, 'score/ddm', sc, st['score'], ddm, st['ddm']))
all5 = [i for i in res if res[i]['npass'] == 5]
print('ALL-5 pass count (my gates):', len(all5), all5)
for f, ids in fams.items():
    print(f, 'per gate pass', {k: sum(res[i]['g'][k] for i in ids) for k in ('G1', 'G2', 'G3', 'G4', 'G5')},
          'npass hist', {n: sum(res[i]['npass'] == n for i in ids) for n in range(6)})
print('mismatches vs stored gates:', len(mism))
for m in mism[:20]: print(' ', m)
print('borderline (<1e-6 from a threshold):', border)
# best per family (npass, score) like stored 'best'
F = json.load(open(RES + 'df7_final.json'))
best = {}
for c in C:
    i = c['id']; k = c['fam']; sc = min(rows[i]['P30']['pair'], rows[i]['X30']['pair'], rows[i]['REAL']['cagr'] - Q['REAL']['cagr'])
    key = (res[i]['npass'], sc)
    if k not in best or key > best[k][1]: best[k] = (i, key)
print('best per family (mine):', {k: v[0] for k, v in best.items()}, 'stored:', F['best'])
print('4-of-5 rules:', sorted([(i, res[i]['fail']) for i in res if res[i]['npass'] == 4]))
json.dump(dict(all5=all5, n=len(res), mism=[str(m) for m in mism], border=border, best={k: v[0] for k, v in best.items()}, res=res),
          open('/mnt/project-files/research/df1/verify7/repro/s1_gates_stored.json', 'w'), indent=1)
