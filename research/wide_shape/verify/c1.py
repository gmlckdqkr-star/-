import numpy as np, pandas as pd
from scipy.stats import spearmanr
W='/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/'
K=np.load(W+'kr_arrays.npz',allow_pickle=True); D=np.load(W+'kr_derived.npz',allow_pickle=True)
dates=K['dates']; assert dates.max()<=np.datetime64('2014-12-31')
idx=D['idx']; trade=D['trade']; listed=D['listed']; amt=np.nan_to_num(K['amount'])
T,N=idx.shape
lr=np.log(idx[1:]/idx[:-1]); lr=np.vstack([np.full((1,N),np.nan),lr])
lr=np.where(trade&np.isfinite(lr),lr,np.nan)
def run(fill_last):
    t0=np.argmax(dates>=np.datetime64('1999-01-01'))
    ics=[];dec=[];allm=[];ts=[]
    t=t0
    while t+22<T:
        w=lr[t-62:t+1]; n=np.sum(np.isfinite(w),0)
        sd=np.nanstd(w,0,ddof=1)
        a20=np.nansum(amt[t-19:t+1],0)/20
        age=np.cumsum(listed[:t+1],0)[-1]
        elig=trade[t]&(age>=20)&(a20>=1e8)&(n>=60)&np.isfinite(idx[t+1])
        p1=idx[t+1]; p2=idx[t+22].copy()
        if fill_last:
            # delisted within window: use last valid price before t+22
            seg=idx[t+1:t+23]; 
            ok=np.isfinite(seg); last=np.where(ok.any(0), seg[(T and (np.where(ok,np.arange(seg.shape[0])[:,None],-1).max(0))),np.arange(N)],np.nan)
            p2=np.where(np.isfinite(p2),p2,last)
        ret=p2/p1-1
        e=elig&np.isfinite(ret)
        if e.sum()>=30:
            s=-sd[e]; r=ret[e]
            ics.append(spearmanr(s,r)[0])
            rk=pd.Series(s).rank(pct=True).values
            d=np.minimum((rk*10-1e-9).astype(int),9)+1  # 10=lowest vol (highest s)
            dec.append([r[d==k].mean() for k in range(1,11)]); allm.append(r.mean()); ts.append(t)
        t+=21
    return np.array(ics),np.array(dec),np.array(allm)
for f in (False,True):
    ic,dec,al=run(f)
    print('fill_last',f,'blocks',len(ic),'meanIC %.4f t=%.2f'%(ic.mean(),ic.mean()/ic.std(ddof=1)*np.sqrt(len(ic))))
    print('decile 1(highvol)..10(lowvol) %:',np.round(np.nanmean(dec,0)*100,3)); print('all-elig %.3f'%(al.mean()*100))
    print('D10-all %.3f  D1-all %.3f D5-all %.3f'%((np.nanmean(dec,0)[9]-al.mean())*100,(np.nanmean(dec,0)[0]-al.mean())*100,(np.nanmean(dec,0)[4]-al.mean())*100))
# cross-check vs cached s20-free: also vs raw adj_ret based vol
