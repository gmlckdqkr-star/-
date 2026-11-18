import sys, json, numpy as np, collections
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); idx={c['id']:c for c in D['configs']}
F=json.load(open('/mnt/project-files/research/df1/results/df6_final.json'))
CM=[idx[i] for i in F['gpass']]
keys=[k for k in df6.KEYS if k[0] in ('REAL','X')]
r2,q2=df6.run_set(CM,'N2',None,sleeves=['DEF3'],keys=keys)
cnt=collections.Counter()
for c in CM:
    r=r2[c['id']]; ok={}
    a,q=r['REAL'],q2['REAL']; ok['G1']=a['cagr']>q['cagr'] and 1-abs(a['mdd_med'])/abs(q['mdd_med'])>=0.1-1e-12
    for g,k in (('G4','X30'),('G5','X10')):
        a,q=r[k],q2[k]; ok[g]=a['pair']>0 and a['cagr']>q['cagr'] and a['p10']>=q['p10']-1e-12 and 1-abs(a['mdd_p10'])/abs(q['mdd_p10'])>=0.1-1e-12
    for g,v in ok.items(): cnt[g]+=v
    cnt['G1G4G5']+=all(ok.values())
    n1=D['rows'][c['id']]['X30']; n2=r['X30']
    cnt['dX30med']+=n2['cagr']-n1['cagr']
print('N2 among 47 N1 passers:', dict(cnt), 'mean change X30 median cagr N2-N1 %.4f'%(cnt['dX30med']/len(CM)))
