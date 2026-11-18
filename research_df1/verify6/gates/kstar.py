import os, sys, json, time, numpy as np
os.environ['NUMBA_CACHE_DIR']='/tmp/df6v/gates/nb'; sys.dont_write_bytecode=True
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6, df5run as R
RES='/mnt/project-files/research/df1/results/'
D=json.load(open(RES+'df6_main.json')); idx={c['id']:c for c in D['configs']}; QN1=D['qqq']; rowsN1=D['rows']
TOP=['L|TQQQ|DEF3|R252|e0.60|c0.80','L|TQQQ|DEF3|R252|e0.65|c0.70','L|TQQQ|DEF3|R252|e0.70|c0.60']
KEYS=df6.KEYS
def mygate(r,Q):
    g={}; d={}
    a,q=r['REAL'],Q['REAL']
    g['G1']=(a['cagr']>q['cagr']) and (abs(a['mdd_med'])<=0.9*abs(q['mdd_med'])+1e-12)
    d['G1']=dict(ret=a['cagr']-q['cagr'],ddm=1-abs(a['mdd_med'])/abs(q['mdd_med']))
    for gi,k in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        a,q=r[k],Q[k]; ddm=1-abs(a['mdd_p10'])/abs(q['mdd_p10'])
        cond=dict(pair=a['pair']>0,med=a['cagr']>q['cagr'],p10=a['p10']>=q['p10'],dd=ddm>=0.1-1e-12)
        g[gi]=all(cond.values()); d[gi]=dict(fail=[c for c,v in cond.items() if not v],pair=a['pair'],med=a['cagr']-q['cagr'],p10=a['p10']-q['p10'],ddm=ddm)
    return g,d
CACHE={}; NEVAL=[0]; KN1={}
def evalk(ids,k):
    C=[idx[i] for i in ids]; rows={i:{} for i in ids}; Q={}
    for wname in ('REAL','P','X'):
        X=df6.W6(wname,'N3',{'DEF3':k},['DEF3'])
        if wname not in KN1:
            sel=np.zeros((X.P,X.T),bool); sel[:,df6.WARM:]=True; rf=np.nan_to_num(X.m['rf'])
            KN1[wname]=dict(kN1=float((X.pan['SPX'][0]-rf)[sel].std()/(X.pan['DEF3'][0]-rf)[sel].std()), shift_ann=X.pan['meta']['shift6']['DEF3'])
        for wn,h,key in [kk for kk in KEYS if kk[0]==wname]:
            hh=None if h==30 else h
            qcg,qmd,_=df6.bench(X,hh); Q[key]=R.summ(qcg,qmd)
            for c in C:
                cg,md,_=df6.run(c,X,hh); rows[c['id']][key]=R.summ(cg,md,qcg)
        del X; df6.drop(wname); NEVAL[0]+=len(C)
    out={}
    for i in ids:
        g,d=mygate(rows[i],Q); out[i]=dict(g=g,d=d,ok=all(g.values()),rows=rows[i])
        CACHE[(i,round(k,6))]=out[i]
    return out,Q
t0=time.time(); res={}
# 1) at k_s, k_low and k=1 for all three
kv=df6.KV()['DEF3']; ks=kv['k_all']; kl=kv['k_low']
for k in (ks,kl):
    o,Q=evalk(TOP,k); res['k=%.6f'%k]=dict(Q=Q,cfg={i:dict(g=o[i]['g'],d=o[i]['d']) for i in TOP})
    print('k',k,{i:(o[i]['ok'],[g for g,v in o[i]['g'].items() if not v]) for i in TOP},'%.0fs'%(time.time()-t0),flush=True)
    if k==ks: print('kN1 implied (daily sigma ratio) per world',KN1,flush=True)
# 2) bisection per config in [1.0,2.0], resolution 0.02
def ok(i,k):
    key=(i,round(k,6))
    if key not in CACHE: evalk([i],k)
    return CACHE[key]['ok']
ks_star={}
for i in TOP:
    lo,hi=1.0,2.0
    if not ok(i,hi): ks_star[i]=dict(kstar=None,note='fails at 2.0'); continue
    if ok(i,lo): ks_star[i]=dict(kstar=lo,note='passes at 1.0'); continue
    while hi-lo>0.02:
        mid=(lo+hi)/2
        if ok(i,mid): hi=mid
        else: lo=mid
    # record failing gates just below k*
    ks_star[i]=dict(kstar=hi,lo_fail=lo,fail_at_lo=[g for g,v in CACHE[(i,round(lo,6))]['g'].items() if not v],
                    d_at_lo=CACHE[(i,round(lo,6))]['d'])
    print(i,ks_star[i]['kstar'],'lo',lo,ks_star[i]['fail_at_lo'],'%.0fs'%(time.time()-t0),flush=True)
res['kstar']=ks_star; res['KN1']=KN1; res['neval_config_world']=NEVAL[0]
json.dump(res,open('/tmp/df6v/gates/kstar_out.json','w'),indent=1,default=float)
print('done evals',NEVAL[0],'%.0fs'%(time.time()-t0))
