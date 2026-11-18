import numpy as np, json, pickle
D=json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
rows=D['rows']; Qj=D['qqq']
z=np.load('/tmp/df5w/df5_arr.npz')
uniq,dups=pickle.load(open('/tmp/df5v/gates/uniq.pkl','rb'))
# dup check across all worlds
for g in dups:
    for i in g[1:]:
        d=max(float(np.max(np.abs(z[i+'||'+w].astype(np.float64)-z[g[0]+'||'+w].astype(np.float64)))) for w in ['REAL','P30','P10','X30','X10'])
        print('dup', i, 'vs', g[0], 'max diff all worlds', d)
# near-dup scan: unique configs whose P30 fin differ < 1e-6 relative
fin=np.array([z[i+'||finP30'].astype(np.float64) for i in uniq])
lf=np.log(np.maximum(fin,1e-300))
from itertools import combinations
# sort by first column to find candidates
o=np.lexsort(lf[:,:3].T[::-1]); near=[]
for a,b in zip(o[:-1],o[1:]):
    if np.max(np.abs(lf[a]-lf[b]))<1e-6: near.append((uniq[a],uniq[b],np.max(np.abs(lf[a]-lf[b]))))
print('near-dups (adjacent in sort, log diff<1e-6):', len(near)); [print('  ',x) for x in near[:20]]
# full pairwise near check by hashing rounded logs to 1e-6
from collections import defaultdict
hh=defaultdict(list)
for k,i in enumerate(uniq): hh[np.round(lf[k],5).tobytes()].append(i)
print('groups equal at 1e-5 log rounding:', [v for v in hh.values() if len(v)>1][:20])
