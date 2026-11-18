import sys, json, numpy as np
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
for V in ('TQQQ','QLD'):
    g=df6.grid(V); m=df6.MULT[V]
    err=max(abs(a*m+b-ei/20) for ei,ci,a,b in g); errs=max(abs(a+b+ci/20-1) for ei,ci,a,b in g)
    print(V, len(g), 'max c', max(ci for _,ci,_,_ in g)/20, 'a=0 pts', sum(a==0 for _,_,a,_ in g), 'exposure err', err, 'sum err', errs, 'min b', min(b for *_,b in g))
C=df6.configs(); print('configs', len(C), {r:sum(c['role']==r for c in C) for r in ('main','report','neg')}, 'main unique', sum(c['role']=='main' and not c['dup_of'] for c in C))
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); F=json.load(open('/mnt/project-files/research/df1/results/df6_final.json'))
idx={c['id']:c for c in D['configs']}; G1=D['gates']; gp=F['gpass']
print('N3ks passers', [i for i in gp if F['H'][i]['N3ks']])
print('H5 (N2) passers', [i for i in gp if F['H'][i]['H5']])
# exercise selection code path with a hypothetical tier = all 47
def nscore(i):
    nb=df6.nbrs(idx[i],idx,1); return min([G1[i]['score']]+[G1[j]['score'] for j in nb])
ns={i:nscore(i) for i in gp}; top=max(ns.values()); tied=[i for i in gp if ns[i]>=top-0.0005]
ans=max(tied,key=lambda i:G1[i]['ddm']); alt=max(gp,key=lambda i:(G1[i]['ddm'],ns[i]))
print('hypothetical answer', ans, 'nscore %.4f'%ns[ans], 'tied', len(tied), 'alt', alt)
print('top raw score', max(gp,key=lambda i:G1[i]['score']), '%.4f'%max(G1[i]['score'] for i in gp))
st=df6.stability(gp, ans, D['rows'], D['qqq'], idx, nrep=200)
print('stability (hypothetical tier=all 47, 200 reps)', st)
