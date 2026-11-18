import os, sys, numpy as np, pandas as pd
for p in ('c3_relax','c3_invent','c3_combo'): sys.path.insert(0,'/mnt/project-files/research/%s/code'%p)
import jp, iv
a,b,P,blk,seed=iv.POOLS['dev250']; R,M=jp.calendar(a,b); X=jp.mkX(R,M,'NDX'); del R,M
assert X.index.max()<=pd.Timestamp('2014-12-31')
ii=np.load('/tmp/df5v/gates/iiX.npy'); r=X['r'].fillna(0).values[ii]; rf=X['rf'].values[ii]
z=np.load('/tmp/df5w/df5_arr.npz')
for h,key in ((30,'X30'),(10,'X10')):
    rr=r[:,300:300+h*252]
    # QQQ proxy: price r + 0.55% div*(1-0.154) - 0.20% fee, pre-tax
    x=rr+(0.0055*(1-0.154)-0.002)/252
    E=np.cumprod(1+x,axis=1); mdd=np.min(E/np.maximum.accumulate(E,axis=1)-1,axis=1)
    cagr=E[:,-1]**(1/h)-1
    qc,qm=z['QQQ||'+key].astype(float)
    print(key,'my pre-tax QQQ proxy: CAGR p10/p50/p90 %s  MDD p10/p50/p90 %s' % (np.round(np.percentile(cagr,[10,50,90])*100,2), np.round(np.percentile(mdd,[10,50,90])*100,2)))
    print(key,'stored QQQ (after tax):  CAGR p10/p50/p90 %s  MDD p10/p50/p90 %s  min MDD %.2f max MDD %.2f' % (np.round(np.percentile(qc,[10,50,90])*100,2), np.round(np.percentile(qm,[10,50,90])*100,2), qm.min()*100, qm.max()*100))
    print('   corr(my mdd, stored mdd) %.4f ; corr(my cagr, stored cagr) %.4f ; median |mdd diff| %.4f' % (np.corrcoef(mdd,qm)[0,1], np.corrcoef(cagr,qc)[0,1], np.median(np.abs(mdd-qm))))
    print('   P(stored QQQ MDD < -30%%)=%.3f  < -40%%=%.3f  < -50%%=%.3f' % (np.mean(qm<-.3),np.mean(qm<-.4),np.mean(qm<-.5)))
# P world sanity, same proxy
gP=np.random.default_rng(7); n=len(X); T=300+30*252; nb=T//250+1
stP=gP.integers(1,n-250,(500,nb)); iiP=(stP[:,:,None]+np.arange(250)[None,None,:]).reshape(500,-1)[:,:T]
for h,key in ((30,'P30'),(10,'P10')):
    rr=X['r'].fillna(0).values[iiP][:,300:300+h*252]; x=rr+(0.0055*(1-0.154)-0.002)/252
    E=np.cumprod(1+x,axis=1); mdd=np.min(E/np.maximum.accumulate(E,axis=1)-1,axis=1)
    qc,qm=z['QQQ||'+key].astype(float)
    print(key,'my MDD p10/p50 %s stored %s corr %.4f' % (np.round(np.percentile(mdd,[10,50])*100,2), np.round(np.percentile(qm,[10,50])*100,2), np.corrcoef(mdd,qm)[0,1]))
