import numpy as np
W='/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/'
z=np.load(W+'ctx_r.npz'); r=z['real_ndx_86_14_r'][0]; rf=z['real_ndx_86_14_rf'][0]
L3=3*r-2*rf-0.0245/252; I3=-3*r+rf-0.0245/252-3*0.015/252; C=(rf-0.02/252)*0.846
S=300; n=len(r); print('days',n, 'ann r mean',r.mean()*252)
def blocks(x):
    out=[];i=S
    while i<n:
        j=min(i+21,n); out.append(np.prod(1+x[i:j])); i=j
    return np.array(out)
bL,bI,bC=blocks(L3),blocks(I3),blocks(C)
def sim(a,b,cost=0.003,tax=0.22,ex=0.25):
    V=1.0; pos=None; basis=0; real=0.0; T=n-S; paid=0
    pick=np.where(a>=b,0,1)
    for k in range(len(a)):
        if k>0 and k%12==0:
            t=tax*max(0,real-ex); V-=t; 
            if pos is not None: pass
            real=0.0
            # tax paid from holding: scale basis? keep basis unchanged (cash taken proportionally from value => reduces gain base). use proportional
            sc=V/(V+t); basis*=sc
        if pick[k]!=pos:
            if pos is not None:
                V*= (1-cost); real+=V-basis
            V*=(1-cost); basis=V; pos=pick[k]
        V*= (a if pick[k]==0 else b)[k]
    V*=(1-cost); real+=V-basis
    V-=tax*max(0,real-ex)
    return V,T,(pick[1:]!=pick[:-1]).sum()
for name,b in (('L3/I3',bI),('L3/cash',bC)):
    for tax in (0.22,0.0):
        V,T,sw=sim(bL,b,tax=tax); print(name,'tax',tax,'final %.3g'%V,'T',T,'switches',sw,'CAGR %.1f%%'%((V**(252/T)-1)*100))
V,T,sw=sim(bL,bI,cost=0,tax=0); print('L3/I3 no cost no tax CAGR %.1f%%'%((V**(252/T)-1)*100))
print('NDX buy&hold ann geo %.1f%%'%((np.prod(1+r[S:])**(252/(n-S))-1)*100))
