import numpy as np, json, pickle, hashlib
from collections import Counter
D=json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
rows=D['rows']; Qj=D['qqq']
z=np.load('/tmp/df5w/df5_arr.npz')
ids=list(rows.keys())
# dedupe by finP30
fin={i:z[i+'||finP30'].astype(np.float64) for i in ids}
groups={}
for i in ids:
    h=hashlib.sha1(np.round(fin[i],12).tobytes()).hexdigest(); groups.setdefault(h,[]).append(i)
dups=[g for g in groups.values() if len(g)>1]
print('dup groups', len(dups), 'dropped', sum(len(g)-1 for g in dups))
for g in dups: print('  ', g)
# also exact equality / near-equality check
F=np.array([fin[i] for i in ids]); print('fin shape',F.shape)
# near-dups with tolerance 1e-9 relative
uniq=[g[0] for g in groups.values()]
uniq=[i for i in ids if i in set(uniq)]
print('N_unique', len(uniq))
S,q=pickle.load(open('/tmp/df5v/gates/S.pkl','rb'))
QR=q['REAL'].ravel()
def gates(i, margin=0.1, use='json'):
    r=rows[i]; g={}
    a=r['REAL']; g['G1']= (a['cagr']>Qj['REAL']['cagr']) and (abs(a['mdd_med'])<= (1-margin)*abs(Qj['REAL']['mdd_med'])+1e-12)
    for gn,w in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a=r[w]; Q=Qj[w]
        c=dict(pair=a['pair']>0, med=a['cagr']>Q['cagr'], p10=a['p10']>=Q['p10']-1e-12, dd=abs(a['mdd_p10'])<=(1-margin)*abs(Q['mdd_p10'])+1e-12)
        g[gn]=all(c.values()); g[gn+'c']=c
    return g
G={i:gates(i) for i in uniq}
single={k:sum(G[i][k] for i in uniq) for k in ['G1','G2','G3','G4','G5']}
print('single (unique)', single)
print('single (all 2324)', {k:sum(gates(i)[k] for i in ids) for k in ['G1','G2','G3','G4','G5']})
allp=[i for i in uniq if all(G[i][k] for k in ['G1','G2','G3','G4','G5'])]
print('pass all', len(allp))
# count of gates passed distribution
print('npass dist', Counter(sum(G[i][k] for k in ['G1','G2','G3','G4','G5']) for i in uniq))
# combos
print('G1&G2', sum(G[i]['G1'] and G[i]['G2'] for i in uniq), 'G1&G2&G3', sum(G[i]['G1'] and G[i]['G2'] and G[i]['G3'] for i in uniq), 'G2&G3', sum(G[i]['G2'] and G[i]['G3'] for i in uniq))
# per-condition counts in G4,G5
for gn in ['G2','G3','G4','G5']:
    print(gn, {c:sum(G[i][gn+'c'][c] for i in uniq) for c in ['pair','med','p10','dd']}, 'pair&dd', sum(G[i][gn+'c']['pair'] and G[i][gn+'c']['dd'] for i in uniq), 'all-but-dd', sum(G[i][gn+'c']['pair'] and G[i][gn+'c']['med'] and G[i][gn+'c']['p10'] for i in uniq))
# also using my own array-derived stats instead of json (robustness)
def gates_arr(i):
    s=S[i]; g={}
    g['G1']=(s['REAL']['cagr']>QR[0]) and abs(s['REAL']['mdd'])<=0.9*abs(QR[1])+1e-12
    for gn,w in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a=s[w]; Q=Qj[w]
        g[gn]= a['pair']>0 and a['cagr']>Q['cagr'] and a['p10']>=Q['p10']-1e-12 and abs(a['mdd_p10'])<=0.9*abs(Q['mdd_p10'])+1e-12
    return g
GA={i:gates_arr(i) for i in uniq}
print('single (arrays)', {k:sum(GA[i][k] for i in uniq) for k in ['G1','G2','G3','G4','G5']}, 'pass all', sum(all(GA[i].values()) for i in uniq))
# Which G2 / G3 passers, and their G1/G4/G5 status
for i in uniq:
    if G[i]['G2'] or G[i]['G3']:
        print('%-55s G1=%d G2=%d G3=%d G4=%d G5=%d  X30fail=%s' % (i, G[i]['G1'],G[i]['G2'],G[i]['G3'],G[i]['G4'],G[i]['G5'], [c for c,v in G[i]['G4c'].items() if not v]))
pickle.dump((uniq,dups),open('/tmp/df5v/gates/uniq.pkl','wb'))
# fam counts
print(Counter(rows[i]['fam'] for i in uniq))
