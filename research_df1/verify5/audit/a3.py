import sys, json, numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5gate as GT
A, G, D = GT.analyse()
print('N_raw', A['N_raw'], 'N_unique', A['N_unique'], 'dups', A['dups'], 'passers', A['passers'], 'single', A['single'], 'xboth', A['xboth'])
# independent recount from arrays
arr = np.load('/tmp/df5w/df5_arr.npz')
Q = {k: arr['QQQ||'+k] for k in ['REAL','P30','P10','X30','X10']}
rows = D['rows']
cnt = {k:0 for k in ['G1','G2','G3','G4','G5']}; allp = 0
mism = 0
for i in rows:
    if i in GT.dedupe([i], {}) : pass
ids = list(rows.keys())
dup = GT.dedupe(ids, dict(arr))
for i in ids:
    if i in dup: continue
    ok = {}
    c = arr[i+'||REAL']; q = Q['REAL']
    ok['G1'] = c[0][0] > q[0][0] and abs(c[1][0]) <= 0.9*abs(q[1][0]) + 1e-12
    for g, k in zip(['G2','G3','G4','G5'], ['P30','P10','X30','X10']):
        c = arr[i+'||'+k].astype(np.float64); q = Q[k].astype(np.float64)
        ok[g] = (np.median(c[0]-q[0]) > 0) and (np.median(c[0]) > np.median(q[0])) and (np.percentile(c[0],10) >= np.percentile(q[0],10)) and (abs(np.percentile(c[1],10)) <= 0.9*abs(np.percentile(q[1],10)))
    for g in ok: cnt[g] += ok[g]
    allp += all(ok.values())
    if any(ok[g] != G[i]['g'][g]['ok'] for g in ok): mism += 1
print('recount from float32 arrays', cnt, 'all', allp, 'mismatch vs json', mism)
