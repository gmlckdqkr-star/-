# joint-draw sensitivity: reproduce neigh's joint draws (seed 7, vwin U[10,60]) and redo with vwin log-uniform [10,40] (geometric centre 20)
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/neigh')
import neighlib as NL
DC=NL.DC; t0=time.time()
BASE={bn: DC.market(bn) for bn in DC.SEL}
def joint(p, mode, n=100):
    cfg0=NL.ALLC[NL.PICKS[p]]; bud=NL.BUD[p]; rng=np.random.default_rng(7); J=[]
    for j in range(n):
        e=dict(sl=int(rng.integers(150,251)), bd=float(rng.uniform(.01,.03)), vc=float(rng.uniform(.35,.45)), vwin=int(rng.integers(10,61)))
        k=dict(ks=float(rng.uniform(.8,1.2)), kfl=float(rng.uniform(0,.5)), step_lo=float(rng.uniform(.05,.15)))
        ds=float(rng.uniform(-.025,.025))
        if mode=='logc20': e['vwin']=int(round(np.exp(np.log(10)+(e['vwin']-10)/50.0*(np.log(40)-np.log(10)))))  # same draw mapped to log-uniform [10,40]
        if mode=='v20': e['vwin']=20
        cfg=dict(cfg0); cfg['sig']=cfg0['sig']+ds
        M3={bn: NL.env(BASE[bn], **e) for bn in DC.SEL}
        r=NL.flat(NL.run3(cfg, M3, NL.eng_kw(cfg, **k))); J.append((r['path'], r['wd'], r['wd']>=bud))
    a=np.array(J)
    return dict(in_tier=float(a[:,2].mean()), path_med=float(np.median(a[:,0])*100), wd_med=float(np.median(a[:,1])*100))
out={}
for p in ('T25','T30','T40','T40alt'):
    for mode in ('orig','logc20','v20'):
        r=joint(p, mode); out[p+'_'+mode]=r
        print(p, mode, {k: round(v,3) for k,v in r.items()}, '%.0fs'%(time.time()-t0), flush=True)
json.dump(out, open('/tmp/rev_neigh/joint_sens.json','w'), indent=1)
