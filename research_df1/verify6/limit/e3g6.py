import os, sys, json, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, df5stress as ST, df5run as R
def mk(V, Rb, e, c):
    m = D6.MULT[V]; a = (e - 1 + c) / (m - 1); return dict(id='F|%s|R%d|e%.3f|c%.3f' % (V, Rb, e, c), V=V, R=Rb, a=a, b=1 - c - a, c=c)
GR = D6.g6_world('R2885'); GO = D6.g6_world('OLD6'); out = {}
for c in (mk('TQQQ', 63, 0.700, 0.625), mk('TQQQ', 63, 0.675, 0.675)):
    cg, md, qcg, qmd = D6.g6_run(c, GR); a = ST.gate_conds(cg, md, qcg, qmd, True)
    cg2, md2, qcg2, qmd2 = D6.g6_run(c, GO); b = ST.gate_conds(cg2, md2, qcg2, qmd2)
    out[c['id']] = dict(R2885=(float(cg[0]), float(md[0]), float(qcg[0]), float(qmd[0]), bool(a)), OLD6=dict(R.summ(cg2, md2, qcg2), ok=bool(b)))
    print(c['id'], out[c['id']])
json.dump(out, open('/tmp/df6v/limit/e3g6.json', 'w'), indent=1)
