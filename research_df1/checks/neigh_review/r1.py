# independent re-run of selected one-at-a-time variants (own rebuild, not neighlib.env/eng_kw)
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
import px1lib as PX
t0=time.time()
B={bn: DC.market(bn) for bn in DC.SEL}
ALL={c['id']:c for c in RG.configs()+R2.configs()}
def mk(bn, sl=200, bd=.02, vc=.40, vwin=20):
    m=dict(B[bn]); c=m['ctx']
    m['st_v1']=PX.signal(c,('F1',3,vc,'alarm','shock6m',sl,bd)); m['st_al']=PX.signal(c,('F1',3,vc,'always','shock6m',sl,bd))
    m['vol20']=c.vol(vwin); return m
def run(cid, env={}, d0s=1.0, kfl=None, step_lo=None, dsig=0.0):
    cfg=dict(ALL[cid]); cfg['sig']=round(cfg['sig']+dsig,4)
    kn=RG.KNEES[cfg['knee']]; res={}
    for bn in DC.SEL:
        m=mk(bn, **env)
        L=DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax'])
        kw=dict(kon=1, d0=kn['d0']*d0s, d1=kn['d1']*d0s, kfl=kn['kfl'] if kfl is None else kfl, roff=RG.ROFF[cfg['roff']])
        if cfg['fam']=='df2':
            kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M']=='M0' else 2)
        if step_lo is not None: kw['step_lo']=step_lo
        o,_=dfe.run(m, L, **kw); cg,md=dfe.stats(o, m['r'].shape[1])
        if bn=='dev250_path': res.update(path=np.median(cg), mddp10=np.percentile(md,10))
        else: res[bn]=(cg[0], md[0])
    res['wd']=min(res['mddp10'], res['real_ndx_86_14'][1], res['real_spx_29_54'][1])
    return res
P={'T25':'v1|s0.1|L1.0|K1|RB','T30':'v1|s0.2|L1.0|K1|RB','T40':'DF2|M2|b1|v1|s0.3|L1.5|K2|RB','T40alt':'v1|s0.3|L1.0|K2|RB'}
tests=[('T25','base',{},{}),('T25','knee_x1.2',{},dict(d0s=1.2)),('T25','volwin_10',dict(vwin=10),{}),('T25','vcap_0.35',dict(vc=.35),{}),
       ('T25','sigma+',{},dict(dsig=.025)),('T30','base',{},{}),('T30','kfloor_0.5',{},dict(kfl=.5)),('T30','sma_250',dict(sl=250),{}),
       ('T30','steplo_0.15',{},dict(step_lo=.15)),('T40','base',{},{}),('T40','knee_x0.8',{},dict(d0s=.8)),('T40','sma_150',dict(sl=150),{}),
       ('T40alt','kfloor_0.5',{},dict(kfl=.5)),('T40alt','band_0.03',dict(bd=.03),{})]
for p,nm,e,k in tests:
    r=run(P[p], e, **k)
    print('%-6s %-12s path %6.2f mddp10 %6.2f ndx %6.2f/%6.2f spx29 %6.2f/%6.2f WD %7.3f'%(p,nm,100*r['path'],100*r['mddp10'],100*r['real_ndx_86_14'][0],100*r['real_ndx_86_14'][1],100*r['real_spx_29_54'][0],100*r['real_spx_29_54'][1],100*r['wd']),flush=True)
print('%.0fs'%(time.time()-t0))
