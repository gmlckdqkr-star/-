import json, collections
RES='/mnt/project-files/research/df1/results/'
D=json.load(open(RES+'df6_main.json')); C=D['configs']; idx={c['id']:c for c in C}
M=json.load(open('/tmp/df6v/gates/mygates.json')); MG=M['MG']; gp=M['gp']
F=json.load(open(RES+'df6_final.json'))
main=[c for c in C if c['role']=='main']
# own grid index: (V,R,ei,ci) -> canonical id
grid={}
for c in main:
    grid[(c['V'],c['R'],c['ei'],c['ci'])]=c['dup_of'] or c['id']
passset={i for i in grid.values() if all(MG[i].values())}
assert passset==set(gp)
def nb(c, both_for_a0=True):
    Vs=['TQQQ','QLD'] if (c['a']==0 and both_for_a0) else [c['V']]
    me=c['dup_of'] or c['id']; out=set()
    for V in Vs:
        for (v,R,ei,ci),j in grid.items():
            if v==V and R==c['R'] and max(abs(ei-c['ei']),abs(ci-c['ci']))<=2 and j!=me: out.add(j)
    return sorted(out)
def other(c):
    R2=252 if c['R']==63 else 63
    return grid[(c['V'],R2,c['ei'],c['ci'])]
res={}
for i in gp:
    c=idx[i]; n=nb(c); k=sum(j in passset for j in n); o=other(c) in passset
    res[i]=dict(n=len(n),npass=k,frac=k/len(n),other=o)
mism=[i for i in gp if (res[i]['n'],res[i]['npass'],res[i]['other'])!=(F['H'][i]['H4']['n'],F['H'][i]['H4']['npass'],F['H'][i]['H4']['other_R'])]
print('H4 mismatches vs final.json',len(mism),mism[:3])
for th in (0.75,0.6,0.5):
    okn=[i for i in gp if res[i]['n']>=4 and res[i]['npass']>=th*res[i]['n']]
    okall=[i for i in okn if res[i]['other']]
    print('th',th,'nbhd-ok',len(okn),'and otherR',len(okall), okall[:10])
print('otherR pass',sum(res[i]['other'] for i in gp),'of',len(gp))
print('a=0 passers',[i for i in gp if idx[i]['a']==0])
print('n dist',collections.Counter(res[i]['n'] for i in gp))
fr=sorted(res[i]['frac'] for i in gp); print('frac min/median/max',fr[0],fr[len(fr)//2],fr[-1])
for i in sorted(gp,key=lambda i:-res[i]['frac'])[:12]: print(i,res[i])
# variant: a=0 centre only uses own V (TQQQ)
print('variant (a0 centre own V only) same result?')
for i in gp:
    c=idx[i]
    if c['a']==0: print(i,len(nb(c,False)),sum(j in passset for j in nb(c,False)))
json.dump(res,open('/tmp/df6v/gates/h4.json','w'),indent=0)
