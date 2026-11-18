"""E3 verification (report-only): re-run the two NA passers through df6.run_set + df6.gates (official gate code), and
measure fragility by resampling paths (1000x, seed 11) of P30/P10/X30/X10 jointly. <=2014 data only."""
import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, df5run as R, df5stress as ST
kd = D6.KV()['DEF3']; NA = {'DEF3': kd['delta_ann_all'] / np.sqrt(252)}
def mk(V, Rb, e, c):
    m = D6.MULT[V]; a = (e - 1 + c) / (m - 1); return dict(id='F|%s|R%d|e%.3f|c%.3f' % (V, Rb, e, c), role='x', V=V, S='DEF3', R=Rb, e=e, c=c, a=a, b=1 - c - a)
C = [mk('TQQQ', 63, 0.700, 0.625), mk('TQQQ', 63, 0.675, 0.675)]
out = {}
rows, Q = D6.run_set(C, 'NA', NA, sleeves=['DEF3']); G = D6.gates(rows, Q)
out['official'] = {c['id']: dict(npass=G[c['id']]['npass'], score=G[c['id']]['score'], ddm=G[c['id']]['ddm'], fail=G[c['id']]['fail'],
                                 rows=rows[c['id']]) for c in C}
out['qqq'] = Q
print({i: (v['npass'], round(v['score'] * 100, 3), round(v['ddm'], 4)) for i, v in out['official'].items()}, flush=True)
# path-resampling fragility
ARR = {}
for wname in ('P', 'X'):
    X = D6.W6(wname, 'NA', NA, ['DEF3'])
    for h, key in ((None, wname + '30'), (10, wname + '10')):
        qcg, qmd, _ = D6.bench(X, h); ARR[('Q', key)] = (qcg, qmd)
        for c in C:
            cg, md, _ = D6.run(c, X, h); ARR[(c['id'], key)] = (cg, md)
    del X; D6.drop(wname)
rng = np.random.default_rng(11); nrep = 1000; keep = {c['id']: 0 for c in C}; keepg = {c['id']: {k: 0 for k in ('P30', 'P10', 'X30', 'X10')} for c in C}
for _ in range(nrep):
    ix = {'P': rng.integers(0, 500, 500), 'X': rng.integers(0, 500, 500)}
    for c in C:
        ok_all = True
        for key in ('P30', 'P10', 'X30', 'X10'):
            j = ix[key[0]]; cg, md = ARR[(c['id'], key)]; qcg, qmd = ARR[('Q', key)]
            ok = ST.gate_conds(cg[j], md[j], qcg[j], qmd[j]); keepg[c['id']][key] += ok; ok_all &= ok
        keep[c['id']] += ok_all
out['resample'] = {i: dict(all_G2_G5=keep[i] / nrep, **{k: v / nrep for k, v in keepg[i].items()}) for i in keep}
print(out['resample'])
json.dump(out, open('/tmp/df6v/limit/e3v.json', 'w'), indent=1)
