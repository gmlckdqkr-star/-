# synthetic smoke test of engine + stats (random atoms, random returns): code paths only, no real data
import os, sys, time, numpy as np
SCR='/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/'
os.environ['NUMBA_CACHE_DIR']=SCR+'nb'; sys.path.insert(0,SCR+'code')
import m1_engine as EN, m1_stats as ST
rng=np.random.default_rng(1); T=6000; na=50
A=(rng.random((na,T))<0.6).astype(np.int8); A[:, :300]=-1
r=rng.normal(0.0004,0.012,T); rf=np.full(T,0.0002); X=EN.products(r,rf)
rules=np.array([[rng.integers(na),rng.integers(na),rng.integers(na),rng.integers(7),*EN.SHAPE_CODES[rng.integers(7)],[1,5,21][rng.integers(3)]] for _ in range(5000)],np.int64)
mon=np.full(T,-1,np.int64); mon[1000:]=np.arange(T-1000)//21; nmon=mon.max()+1
om=np.zeros((len(rules),nmon),np.float32); os_=np.zeros((len(rules),4))
t=time.time(); EN.screen(A,X,rules,T,mon,nmon,1000,T,om,os_); print('screen', time.time()-t)
t=time.time(); EN.screen(A,X,rules,T,mon,nmon,1000,T,om*0,os_); print('screen2', time.time()-t)
# null: SPA p should be large-ish; RW should reject ~0
res,aux=ST.spa_rw(om,verbose=False); print({k:v for k,v in res.items() if k!='rw_crit'})
print('lead', ST.leader_clusters(om, np.argsort(-aux['tstat']), 0.7), 'lij', ST.lij_meff(om)[0])
# one_path vs screen sums
k=7; d,a,g=EN.one_path(A,X,rules[k],T); print('sum check', g[1000:T].sum(), os_[k,0])
print('dsr', ST.dsr(om[0], np.var(om.mean(1)/om.std(1)), 5000))
