import json, numpy as np, collections
RES='/mnt/project-files/research/df1/results/'
D=json.load(open(RES+'df6_main.json')); C=D['configs']; Q=D['qqq']; rows=D['rows']; G0=D['gates']
idx={c['id']:c for c in C}
def mygate(r):
    g={}
    a,q=r['REAL'],Q['REAL']
    g['G1']=(a['cagr']>q['cagr']) and (abs(a['mdd_med'])<=0.9*abs(q['mdd_med'])+1e-12)
    for gi,k in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a,q=r[k],Q[k]
        g[gi]=(a['pair']>0) and (a['cagr']>q['cagr']) and (a['p10']>=q['p10']) and (abs(a['mdd_p10'])<=0.9*abs(q['mdd_p10'])+1e-12)
    return g
MG={i:mygate(rows[i]) for i in rows}
# compare with stored
mism=[i for i in rows if any(MG[i][k]!=G0[i]['g'][k] for k in MG[i])]
print('gate mismatches vs stored:',len(mism))
# score
def score(i): r=rows[i]; return min(r['P30']['pair'],r['X30']['pair'],r['REAL']['cagr']-Q['REAL']['cagr'])
sm=max(abs(score(i)-G0[i]['score']) for i in rows); print('max score diff',sm)
# dedupe check
dups=[c for c in C if c['dup_of']]
print('n dup',len(dups), collections.Counter(c['role'] for c in dups))
maxd=0; bad=[]
for c in dups:
    j=c['dup_of']; assert idx[j]['a']==0 and c['a']==0
    for k in rows[c['id']]:
        for f in rows[c['id']][k]:
            d=abs(rows[c['id']][k][f]-rows[j][k][f]); maxd=max(maxd,d)
            if d>1e-12: bad.append((c['id'],k,f,d))
print('dup rows max abs diff',maxd,'nbad',len(bad))
# check that a=0 detection is exact: any QLD config with a==0 lacking dup_of? and TQQQ a=0 count
for role in ('main','report','neg'):
    for V in ('TQQQ','QLD'):
        cc=[c for c in C if c['role']==role and c['V']==V]
        print(role,V,len(cc),'a0',sum(c['a']==0 for c in cc),'dup',sum(bool(c['dup_of']) for c in cc))
for role in ('main','report','neg'):
    ids=[c['id'] for c in C if c['role']==role and not c['dup_of']]
    print(role,'unique',len(ids),'all5',sum(all(MG[i].values()) for i in ids),{k:sum(MG[i][k] for i in ids) for k in ('G1','G2','G3','G4','G5')})
for S in ['DEF3','STAP','HLTH','UTIL','DEF2','ENER','MANU','SHOP','FIN','TELE','SPX']:
    ids=[c['id'] for c in C if c['S']==S and not c['dup_of']]
    print(S,len(ids),'all5',sum(all(MG[i].values()) for i in ids),{k:sum(MG[i][k] for i in ids) for k in ('G1','G2','G3','G4','G5')})
main=[c['id'] for c in C if c['role']=='main' and not c['dup_of']]
gp=[i for i in main if all(MG[i].values())]
F=json.load(open(RES+'df6_final.json'))
print('gpass equal to final.json:',sorted(gp)==sorted(F['gpass']))
# by V,R
print(collections.Counter((idx[i]['V'],idx[i]['R']) for i in gp))
top=sorted(gp,key=lambda i:-score(i))[:8]
for i in top: print(i,'score %.5f'%score(i),idx[i]['a'],idx[i]['b'],idx[i]['c'])
json.dump(dict(MG={i:MG[i] for i in rows},gp=gp),open('/tmp/df6v/gates/mygates.json','w'))
# near-misses: how close to the 0.9 rule etc
