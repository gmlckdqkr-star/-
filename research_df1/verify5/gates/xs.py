import os, sys, numpy as np, pandas as pd
for p in ('c3_relax','c3_invent','c3_combo'): sys.path.insert(0,'/mnt/project-files/research/%s/code'%p)
import jp, iv
a,b,P,blk,seed=iv.POOLS['dev250']; R,M=jp.calendar(a,b); assert R.index.max()<=pd.Timestamp('2014-12-31')
ii=np.load('/tmp/df5v/gates/iiX.npy')[:,300:]
n=len(R); T=300+30*252; nb=T//250+1
gP=np.random.default_rng(7); stP=gP.integers(1,n-250,(500,nb)); iiP=(stP[:,:,None]+np.arange(250)[None,None,:]).reshape(500,-1)[:,300:T]
for s in ['NDX','SPX']:
    r=R[s].fillna(0).values
    print(s,'ann. arith mean: source %.4f  P %.4f  X %.4f | ann vol X %.4f'%(r.mean()*252, r[iiP].mean()*252, r[ii].mean()*252, r[ii].std()*np.sqrt(252)))
rf=M['rf'].values; print('rf ann mean: X %.4f  P %.4f'%(rf[ii].mean()*252, rf[iiP].mean()*252))
