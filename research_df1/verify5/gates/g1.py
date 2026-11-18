import numpy as np, json, hashlib
from collections import Counter
D=json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
rows=D['rows']; Qj=D['qqq']
z=np.load('/tmp/df5w/df5_arr.npz')
A={k:z[k] for k in z.keys()}
ids=list(rows.keys())
print('N ids', len(ids), 'unique id strings', len(set(ids)))
W=['P30','P10','X30','X10']
q={w:A['QQQ||'+w].astype(np.float64) for w in ['REAL']+W}
# my stats from arrays
def stats(a, qa):
    c=a[0].astype(np.float64); m=a[1].astype(np.float64)
    return dict(cagr=np.median(c), p10=np.percentile(c,10), mdd_med=np.median(m), mdd_p10=np.percentile(m,10),
                pair=np.median(c-qa[0]), win=np.mean(c>qa[0]))
mx=Counter()
S={}
for i in ids:
    S[i]={}
    for w in W:
        s=stats(A[i+'||'+w], q[w]); S[i][w]=s
        for k in s:
            d=abs(s[k]-rows[i][w][k]); mx[(w,k)]=max(mx[(w,k)],d)
    a=A[i+'||REAL']; S[i]['REAL']=dict(cagr=float(a[0,0]),mdd=float(a[1,0]))
    mx[('REAL','cagr')]=max(mx[('REAL','cagr')],abs(a[0,0]-rows[i]['REAL']['cagr']))
    mx[('REAL','mdd')]=max(mx[('REAL','mdd')],abs(a[1,0]-rows[i]['REAL']['mdd_med']))
print('max abs diff arrays-vs-json', dict(mx))
for w in W:
    s=stats(q[w],q[w]); print('QQQ',w,{k:round(v,5) for k,v in s.items()}, 'json', {k:round(Qj[w][k],5) for k in ('cagr','p10','mdd_med','mdd_p10')})
print('QQQ REAL', q['REAL'].ravel(), Qj['REAL']['cagr'], Qj['REAL']['mdd_med'])
import pickle; pickle.dump((S,{w:q[w] for w in q}),open('/tmp/df5v/gates/S.pkl','wb'))
