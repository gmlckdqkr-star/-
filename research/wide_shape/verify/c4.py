import numpy as np, pandas as pd
from scipy.stats import spearmanr
W='/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/'
z=np.load(W+'us_v3.npz',allow_pickle=True)
T,N=z['shape']; d=pd.to_datetime(z['dates'],unit='D'); keep=np.asarray(d<=pd.Timestamp('2014-12-31'))
d=d[keep]; adj=z['adj'][keep].astype(float); mem=np.unpackbits(z['member'],axis=0)[:T][keep].astype(bool)
print(d[0],d[-1],adj.shape)
first=np.where(mem.any(0),mem.argmax(0),10**9)
P=adj.copy(); 
for j in range(N):
    if first[j]<10**9: P[:first[j],j]=np.nan
    else: P[:,j]=np.nan
t=np.argmax(d>=pd.Timestamp('1971-01-01')); ics=[]
Tn=len(d)
while t+22<Tn:
    ok=mem[t]&np.isfinite(P[t])&np.isfinite(P[t+1])&np.isfinite(P[t+22])&np.isfinite(P[t-21])&np.isfinite(P[t-252])&(P[t+1]>0)&(P[t-252]>0)
    if ok.sum()>=30:
        s=P[t-21,ok]/P[t-252,ok]-1; r=P[t+22,ok]/P[t+1,ok]-1
        ics.append(spearmanr(s,r)[0])
    t+=21
ics=np.array(ics); print('blocks',len(ics),'meanIC %.4f t=%.2f'%(ics.mean(),ics.mean()/ics.std(ddof=1)*np.sqrt(len(ics))))
