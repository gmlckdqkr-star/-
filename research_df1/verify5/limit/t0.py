import os, sys, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
t0 = time.time()
import numpy as np
import df5run as R, df5stress as ST, df5lib as L, df5data as DD
print('import', time.time() - t0, flush=True)
X = R.W('X'); print('world', time.time() - t0, X.P, X.T, flush=True)
qcg, qmd, _ = R.qqq(X); print('qqq', R.summ(qcg, qmd), time.time() - t0, flush=True)
idx = ST.cfg_index()
for cid in ['A3|e1.00|c0.20|DEF3|none', 'A1|N|V0.30w20L1.5|DEF3']:
    cg, md, _ = ST.runner(idx[cid], X); print(cid, R.summ(cg, md, qcg), time.time() - t0, flush=True)
print('meta shift', {k: round(v*252, 4) for k, v in X.pan['meta']['shift'].items()})
print('missing', X.pan['meta']['missing'])
