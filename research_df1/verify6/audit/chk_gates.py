import json, sys, collections
sys.path.insert(0,'/mnt/project-files/research/df1/code')
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json'))
C=D['configs']; idx={c['id']:c for c in C}; Q=D['qqq']; rows=D['rows']; G=D['gates']
print('qqq', {k:(round(v['cagr']*100,3), round(v['p10']*100,3), round(v['mdd_med']*100,2), round(v['mdd_p10']*100,2)) for k,v in Q.items()})
D5=json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
print('df5 qqq', {k:(round(v['cagr']*100,3), round(v['p10']*100,3), round(v['mdd_med']*100,2), round(v['mdd_p10']*100,2)) for k,v in D5['qqq'].items()})
# own gate computation
def gate(r):
    ok={}
    a,q=r['REAL'],Q['REAL']; ok['G1']= a['cagr']>q['cagr'] and 1-abs(a['mdd_med'])/abs(q['mdd_med'])>=0.1-1e-12
    for g,k in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a,q=r[k],Q[k]; ok[g]= a['pair']>0 and a['cagr']>q['cagr'] and a['p10']>=q['p10']-1e-12 and 1-abs(a['mdd_p10'])/abs(q['mdd_p10'])>=0.1-1e-12
    return ok
for role in ('main','report','neg'):
    ids=[c['id'] for c in C if c['role']==role and not c['dup_of']]
    mine={i:gate(rows[i]) for i in ids}
    npass=sum(all(v.values()) for v in mine.values())
    single={g:sum(v[g] for v in mine.values()) for g in ['G1','G2','G3','G4','G5']}
    agree=all(all(mine[i].values())==(G[i]['npass']==5) for i in ids)
    print(role, len(ids), npass, single, 'agree', agree)
# dup check: dup rows equal to canonical?
md=0
for c in C:
    if c['dup_of']:
        a=rows[c['id']]; b=rows[c['dup_of']]
        for k in a:
            for f in a[k]: md=max(md,abs(a[k][f]-b[k][f]))
print('max diff dup vs canonical', md)
# counts per sleeve
for S in ['DEF3','STAP','HLTH','UTIL','DEF2']:
    ids=[c['id'] for c in C if c['S']==S and not c['dup_of']]
    print(S, len(ids), sum(G[i]['npass']==5 for i in ids))
