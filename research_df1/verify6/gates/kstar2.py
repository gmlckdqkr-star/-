import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR']='/tmp/df6v/gates/nb'; sys.dont_write_bytecode=True
sys.path.insert(0,'/mnt/project-files/research/df1/code'); sys.path.insert(0,'/tmp/df6v/gates')
import df6
RES='/mnt/project-files/research/df1/results/'
D=json.load(open(RES+'df6_main.json')); idx={c['id']:c for c in D['configs']}
from importlib import util
i='L|TQQQ|DEF3|R63|e0.65|c0.75'
def mygate(r,Q):
    g={}
    a,q=r['REAL'],Q['REAL']; g['G1']=(a['cagr']>q['cagr']) and (abs(a['mdd_med'])<=0.9*abs(q['mdd_med'])+1e-12)
    for gi,k in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a,q=r[k],Q[k]; g[gi]=(a['pair']>0) and (a['cagr']>q['cagr']) and (a['p10']>=q['p10']) and (abs(a['mdd_p10'])<=0.9*abs(q['mdd_p10'])+1e-12)
    return g
def ok(k):
    r,Q=df6.run_set([idx[i]],'N3',{'DEF3':k},sleeves=['DEF3']); g=mygate(r[i],Q); print('k %.4f'%k,g,{kk:round(r[i][kk]['pair'],4) for kk in ['P30','P10','X30','X10']},flush=True); return all(g.values())
lo,hi=0.942882,1.135195
while hi-lo>0.02:
    mid=(lo+hi)/2
    if ok(mid): hi=mid
    else: lo=mid
print('kstar',i,'in (%.4f, %.4f]'%(lo,hi))
