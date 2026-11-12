import sys, json; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, numpy as np, pandas as pd
from gx1lib import std, ov
o=json.load(open('/mnt/project-files/research/gx1/results/foreign_le2014.json')); H=o['hosts']; J=o['J']
for h in ('UK','NZ'):
    X,i0=G.host(h); F=ov.flags_hist(X); rows=np.arange(i0,len(X)); N=len(rows); D=G.world_signals(X.index,h); g=D['G11'].values.astype(bool)
    dates=X.index[i0+G.W:]; m1=(dates<=pd.Timestamp('2006-12-31')); m1[0]=False; m2=dates>=pd.Timestamp('2007-01-01')
    def run(gg): c=ov.Ctx(X,F,rows[None,:]); cg,E=G.acct(c,Ghist=gg,mode='CAP1'); return cg[0], np.log(E[0])
    v=G.acct(ov.Ctx(X,F,rows[None,:]))[0][0]; lv=np.log(G.acct(ov.Ctx(X,F,rows[None,:]))[1][0])
    a,la=run(g); inc=np.diff(np.r_[0,la-lv]); inc[0]=0
    era=[inc[m1].sum(), inc[m2].sum()]
    ds=[]; es=[]
    for j in range(J):
        s=504+63*j
        gs=g.copy(); gs[rows]=np.concatenate([g[rows][-s:], g[rows][:-s]])   # independent circular shift
        b,lb=run(gs); ds.append(b-v); ii=np.diff(np.r_[0,lb-lv]); ii[0]=0; es.append([ii[m1].sum(), ii[m2].sum()])
    es=np.array(es)
    print(h,'d %.6f json %.6f | e %.6f json %.6f | era_e %s json %s | d_shift max abs diff %.2e | N %d max shift %d'%(a-v,H[h]['d'][24],(a-v)-np.median(ds),H[h]['e'][24],
          np.round([era[0]-np.median(es[:,0]), era[1]-np.median(es[:,1])],6), np.round(H[h]['era_e'][24],6), np.max(np.abs(np.array(ds)-np.array(H[h]['d_shift'][24]))), N, 504+63*(J-1)))
