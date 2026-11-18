import sys, json, numpy as np
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); idx={c['id']:c for c in D['configs']}
c=idx['L|TQQQ|DEF3|R252|e0.60|c0.80']
for k in (1.155,1.165):
    r2,q2=df6.run_set([c],'N3',{'DEF3':k},sleeves=['DEF3']); g=df6.gates(r2,q2)[c['id']]
    print('k',k,'npass',g['npass'],'fail',g['fail'],'score %.4f ddm %.4f'%(g['score'],g['ddm']))
X=df6.W6('REAL','N1',None,['DEF3']); print('REAL nanfrac', {k:v for k,v in X.pan['meta']['nanfrac'].items() if k in ('DEF3','STAP','HLTH','UTIL')})
