import os, sys, json, time, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR']='/tmp/df6v/critic/numba'
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6, df5lib as L, df5stress as ST
R='/mnt/project-files/research/df1/results/'
# 1) X-world crash windows (dates <= 2014 only)
a,b,P,blk,seed=L.iv.POOLS['dev250']; X,S=L._src(a,b,'NDX'); print('dev250 pool',a,b,P,blk,seed, 'src range',X.index.min().date(),X.index.max().date())
lv=np.cumprod(1+X['r'].fillna(0).values); D=X.index; n=len(X)
pos=lambda d:int(D.searchsorted(pd.Timestamp(d)))
amax=lambda x,y:pos(x)+int(np.argmax(lv[pos(x):pos(y)])); amin=lambda x,y:pos(x)+int(np.argmin(lv[pos(x):pos(y)]))
tr1=amin('1987-10-01','1988-01-01'); pk1=pos('1987-01-01')+int(np.argmax(lv[pos('1987-01-01'):tr1+1]))
pk2=amax('2000-01-01','2001-01-01'); tr2=pk2+int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3=amax('2007-01-01','2008-07-01'); tr3=amin('2008-07-01','2009-07-01')
for p_,t_ in ((pk1,tr1),(pk2,tr2),(pk3,tr3)):
    e=min(t_+250,n-1); print('excl', D[p_].date(), '->', D[t_].date(), 'dd %.3f'%(lv[t_]/lv[p_]-1), 'excl to', D[e].date())
ii,ns=L._xworld(X,P); print('n starts',ns,'of',n-251)
# share of sampled X days by year bucket
yrs=D.year.values[ii[:,df6.WARM:]]; print('X sampled days in excluded windows:', int(sum(((ii[:,df6.WARM:]>=p_)&(ii[:,df6.WARM:]<=min(t_+250,n-1))).sum() for p_,t_ in ((pk1,tr1),(pk2,tr2),(pk3,tr3)))))
# max drawdown within NDX over the allowed start blocks: worst 250-day block drawdown in X pool
# 2) G6 R2885 for all 47 N1 passers
F=json.load(open(R+'df6_final.json')); M=json.load(open(R+'df6_main.json')); idx={c['id']:c for c in M['configs']}
GR=df6.g6_world('R2885'); out={}; t0=time.time()
mx=-9; nreal=0
for i in F['gpass']:
    cg,md,qcg,qmd=df6.g6_run(idx[i],GR); ok=bool(ST.gate_conds(cg,md,qcg,qmd,single=True))
    ddm=1-abs(md[0])/abs(qmd[0]); st=F['H'][i]['G6']['real_v']
    diff=max(abs(cg[0]-st['cagr']),abs(md[0]-st['mdd']))
    out[i]=dict(cagr=float(cg[0]),mdd=float(md[0]),core=float(qcg[0]),core_mdd=float(qmd[0]),ddm=float(ddm),ok=ok,diff_vs_stored=float(diff))
    mx=max(mx,ddm); nreal+=ok
print('G6 R2885: n',len(out),'passing real cond',nreal,'max ddm %.4f'%mx,'max |diff| vs stored %.2e'%max(v['diff_vs_stored'] for v in out.values()),'%.0fs'%(time.time()-t0))
print('core', round(qcg[0],5), round(qmd[0],5))
json.dump(out,open('/tmp/df6v/critic/g6_all47.json','w'),indent=1)
