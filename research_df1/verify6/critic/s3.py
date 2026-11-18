import os, sys, json, time, numpy as np
os.environ['NUMBA_CACHE_DIR']='/tmp/df6v/critic/numba'
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
R='/mnt/project-files/research/df1/results/'
F=json.load(open(R+'df6_final.json')); M=json.load(open(R+'df6_main.json')); idx={c['id']:c for c in M['configs']}
G=M['gates']; gp=F['gpass']
probe='L|TQQQ|DEF3|R252|e0.60|c0.75'
nb=df6.nbrs(idx[probe],idx,2); fn=[j for j in nb if G[j]['npass']<5]
print('probe nbrs',len(nb),'failing',len(fn))
ids=list(dict.fromkeys(gp+fn)); C=[idx[i] for i in ids]
t0=time.time(); rows,Q=df6.run_set(C,'N1',sleeves=['DEF3']); print('run %.0fs'%(time.time()-t0))
Gn=df6.gates(rows,Q)
md=0; mism=[]
for i in ids:
    for k in rows[i]:
        for f in ('cagr','p10','mdd_med','mdd_p10','pair'):
            a=rows[i][k].get(f); b=M['rows'][i][k].get(f)
            if a is not None and b is not None: md=max(md,abs(a-b))
    if Gn[i]['npass']!=G[i]['npass'] or Gn[i]['g']!=G[i]['g']: mism.append(i)
qd=max(abs(Q[k]['cagr']-M['qqq'][k]['cagr']) for k in Q)
print('configs',len(ids),'max |row diff| %.3e'%md,'QQQ diff %.3e'%qd,'gate mismatches',len(mism))
print('N1 pass among 47:',sum(Gn[i]['npass']==5 for i in gp),' among failing nbrs:',sum(Gn[i]['npass']==5 for i in fn))
for j in fn: print(j, Gn[j]['fail'])
