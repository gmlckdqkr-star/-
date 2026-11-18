"""Neighbour fragility of the off-grid passer e0.70/c0.60 DEF3 (step 0.05), unchanged DF5 engine + gate code."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5gate as GT
EC = [(0.65, 0.60), (0.75, 0.60), (0.70, 0.55), (0.70, 0.65), (0.65, 0.70), (0.75, 0.50), (0.70, 0.75)]
CF = [dict(id='OG|e%.2f|c%.2f' % (e, c), fam='A3', e=e, c=c, dmix=['DEF3'], gate='none') for e, c in EC]
rows = {}; Q = {}
for wname in ('REAL', 'P', 'X'):
    X = R.W(wname); hs = [None] if wname == 'REAL' else [30, 10]
    for h in hs:
        hh = None if h == 30 else h; key = wname + ('' if h is None else str(h))
        qcg, qmd, _ = R.qqq(X, hh); Q[key] = R.summ(qcg, qmd)
        for cfg in CF:
            jb = R.job(cfg, X); cg, md, _ = R.run_job(jb, X, hh); rows.setdefault(cfg['id'], {})[key] = R.summ(cg, md, qcg); del jb
    del X; L._WORLDS.pop(wname, None); DD._P.clear()
for cid, r in rows.items():
    g, sc, ddm = GT.gate_row(r, Q)
    print(cid, 'npass', sum(v['ok'] for v in g.values()), ' '.join('%s:%s(ret/pair %+.2f dd %+.1f%%)' % (k, 'ok' if v['ok'] else 'F', (v.get('pair', v.get('ret'))) * 100, v['ddm'] * 100) for k, v in g.items()))
json.dump(dict(rows=rows, Q=Q), open('/tmp/df5v/critic/nbr.json', 'w'))
