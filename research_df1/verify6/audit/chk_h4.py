import json, collections
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json'))
F=json.load(open('/mnt/project-files/research/df1/results/df6_final.json'))
C=D['configs']; G=D['gates']
main=[c for c in C if c['role']=='main']
# key by (V,R,ei,ci) -> pass
P={}
for c in main:
    P[(c['V'],c['R'],c['ei'],c['ci'])]=(G[c['id']]['npass']==5, c['a'])
def grid_pts(V,R): return {(k[2],k[3]):v for k,v in P.items() if k[0]==V and k[1]==R}
gp=F['gpass']
idx={c['id']:c for c in C}
res=[]
for i in gp:
    c=idx[i]; V,R,ei,ci=c['V'],c['R'],c['ei'],c['ci']
    out={}
    for mode in ('own','union'):
        Vs=[V] if (c['a']>0 or mode=='own') else ['TQQQ','QLD']
        nb={}
        for VV in Vs:
            g=grid_pts(VV,R)
            for (e2,c2),(ok,a2) in g.items():
                if (e2,c2)==(ei,ci): continue
                if max(abs(e2-ei),abs(c2-ci))<=2:
                    nb[(e2,c2) if a2==0 else (VV,e2,c2)]=ok
        n=len(nb); npass=sum(nb.values())
        other=P[(V,252 if R==63 else 63,ei,ci)][0]
        out[mode]=(n,npass,other, n>=4 and npass>=0.75*n and other)
    h=F['H'][i]['H4']
    res.append((i,c['a'],out,h))
for i,a,o,h in res:
    flag='' if (o['union'][0],o['union'][1],o['union'][2])==(h['n'],h['npass'],h['other_R']) else ' MISMATCH'
    print(i,'a=%.3f'%a,o,h['n'],h['npass'],h['other_R'],flag, 'fails=',F['H'][i]['fails'])
