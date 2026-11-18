import sys, json, time, numpy as np
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6, df5run as R, df5data as DD, df5lib as L
wname = sys.argv[1]
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); idx={c['id']:c for c in D['configs']}
K=df6.KV()['DEF3']
t0=time.time()
# 1. DF5 parity of the N1 sleeve return (DEF3)
p5 = DD.panel(wname)            # DF5 N1 panel (raw=False)
p6 = df6.panel6(wname,'N1','dy2',['DEF3'])
p6b = df6.panel6(wname,'N1',None,['DEF3'])
print(wname,'N1 RET maxdiff vs DF5', float(np.max(np.abs(p5['DEF3'][0]-p6['DEF3'][0]))), 'INC dy2', p6['DEF3'][1]*252, 'DF5', p5['DEF3'][1]*252, 'DF6 INC', p6b['DEF3'][1]*252,
      'RET same w/ DYS', float(np.max(np.abs(p6b['DEF3'][0]-p6['DEF3'][0]))))
for k in ('QQQ','TQQQ','QLD','SPX'):
    print('  ',k,'maxdiff vs DF5', float(np.max(np.abs(p5[k][0]-p6[k][0]))))
# 2. Sharpe check under each convention
w=L.world(wname); rf=np.nan_to_num(w['m']['rf']); sel=np.zeros(rf.shape,bool); sel[:,300:]=True
spx=p6['SPX'][0]+0.001/252; xm=spx-rf; shS=xm[sel].mean()/xm[sel].std()
for conv,pa in (('N1',None),('N2',None),('N3',{'DEF3':K['k_all']}),('N3',{'DEF3':K['k_low']}),('NA',{'DEF3':K['delta_ann_all']/np.sqrt(252)}),('N4',None)):
    pp=df6.panel6(wname,conv,pa,['DEF3']); A=pp['DEF3'][0]+df6.ER/252; ex=A-rf
    shA=ex[sel].mean()/ex[sel].std()
    print('  %s %s: DEF3 gross daily Sharpe/S&P = k_impl %.4f  (S&P daily Sh %.5f, Sh diff %.5f) shift(ann) %.4f  mean A ann %.4f  mean SPX ann %.4f  volratio %.3f'%(
        conv, pa, shA/shS, shS, shA-shS, pp['meta']['shift6']['DEF3'], A[sel].mean()*252, spx[sel].mean()*252, ex[sel].std()/xm[sel].std()))
DD._P.clear()
# 3. reproduce top configs + offset-0 parity
X=df6.W6(wname,'N1',None,['DEF3'])
h = None
qcg,qmd,_=df6.bench(X,None)
key={'REAL':'REAL','P':'P30','X':'X30'}[wname]
ids=sys.argv[2].split(',')
for i in ids:
    c=idx[i]
    cg,md,_=df6.run(c,X,None); s=R.summ(cg,md,qcg); st=D['rows'][i][key]
    print('  repro', i, key, 'maxdiff', max(abs(s[f]-st[f]) for f in st))
    cg0,md0,_=df6.run(c,X,None,offset=0)
    print('  offset0 vs reb_every: max|cagr diff| %.3e  max|mdd diff| %.3e'%(np.max(np.abs(cg0-cg)), np.max(np.abs(md0-md))))
    offs=(21,42) if c['R']==63 else (63,126)
    for o in offs:
        cgo,mdo,_=df6.run(c,X,None,offset=o)
        print('  offset',o,'cagr med %.4f mdd p10 %.4f (base %.4f %.4f) gate'%(np.median(cgo),np.percentile(mdo,10),np.median(cg),np.percentile(md,10)), df6.ST.gate_conds(cgo,mdo,qcg,qmd,wname=='REAL'))
print('time %.0f'%(time.time()-t0))
