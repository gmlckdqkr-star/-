import numpy as np, json, pickle
D=json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); rows=D['rows']; Qj=D['qqq']
uniq,_=pickle.load(open('/tmp/df5v/gates/uniq.pkl','rb'))
for w in ['X30','X10']:
    R=pickle.load(open('/tmp/df5v/gates/R_%s.pkl'%w,'rb'))
    pair=np.array([r[1] for r in R]); ddp=np.array([r[2] for r in R]); dmed=np.array([r[6] for r in R]); dp10c=np.array([r[7] for r in R]); ddm=np.array([r[3] for r in R])
    k=np.argmax(np.where(ddp>=0.1,pair,-9)); print(w,'best pair among ddp10>=10%%: %s pair %+.2fpp dd %+.1f%%'%(R[k][0],pair[k]*100,ddp[k]*100))
    k=np.argmax(np.where(pair>0,ddp,-9)); print(w,'best ddp10 among pair>0: %s pair %+.2fpp dd %+.1f%%'%(R[k][0],pair[k]*100,ddp[k]*100))
    print(w,'median-CAGR>QQQ & p10MDD shallower(0 margin): %d; p10CAGR>=QQQ & p10MDD shallower: %d; med>QQQ & medMDD shallower: %d; all3 return conds & dd>=0: %d'%(
        np.sum((dmed>0)&(ddp>=0)), np.sum((dp10c>=0)&(ddp>=0)), np.sum((dmed>0)&(ddm>=0)), np.sum((pair>0)&(dmed>0)&(dp10c>=0)&(ddp>=0))))
i='A3|e1.00|c0.20|GOLD+LTT+DEF3|none'
r=rows[i]
print(i,'REAL cagr %.4f vs %.4f, mdd %.3f vs %.3f'%(r['REAL']['cagr'],Qj['REAL']['cagr'],r['REAL']['mdd_med'],Qj['REAL']['mdd_med']))
for w in ['P30','P10','X30','X10']:
    print('  ',w,'pair %+.3fpp med %+.3fpp p10 %+.3fpp ddp10 %+.2f%%'%(r[w]['pair']*100,(r[w]['cagr']-Qj[w]['cagr'])*100,(r[w]['p10']-Qj[w]['p10'])*100,(1-abs(r[w]['mdd_p10'])/abs(Qj[w]['mdd_p10']))*100))
# G1 pass count sensitivity to margin & G2..G5 at margin 0
def cnt(margin):
    out={}
    out['G1']=sum((rows[i]['REAL']['cagr']>Qj['REAL']['cagr']) and abs(rows[i]['REAL']['mdd_med'])<=(1-margin)*abs(Qj['REAL']['mdd_med'])+1e-12 for i in uniq)
    for g,w in zip(['G2','G3','G4','G5'],['P30','P10','X30','X10']):
        out[g]=sum(rows[i][w]['pair']>0 and rows[i][w]['cagr']>Qj[w]['cagr'] and rows[i][w]['p10']>=Qj[w]['p10']-1e-12 and abs(rows[i][w]['mdd_p10'])<=(1-margin)*abs(Qj[w]['mdd_p10'])+1e-12 for i in uniq)
    allp=sum(all([(rows[i]['REAL']['cagr']>Qj['REAL']['cagr']) and abs(rows[i]['REAL']['mdd_med'])<=(1-margin)*abs(Qj['REAL']['mdd_med'])+1e-12]+[rows[i][w]['pair']>0 and rows[i][w]['cagr']>Qj[w]['cagr'] and rows[i][w]['p10']>=Qj[w]['p10']-1e-12 and abs(rows[i][w]['mdd_p10'])<=(1-margin)*abs(Qj[w]['mdd_p10'])+1e-12 for w in ['P30','P10','X30','X10']]) for i in uniq)
    allpx=sum(all([(rows[i]['REAL']['cagr']>Qj['REAL']['cagr']) and abs(rows[i]['REAL']['mdd_med'])<=(1-margin)*abs(Qj['REAL']['mdd_med'])+1e-12]+[rows[i][w]['pair']>0 and rows[i][w]['cagr']>Qj[w]['cagr'] and rows[i][w]['p10']>=Qj[w]['p10']-1e-12 and abs(rows[i][w]['mdd_p10'])<=(1-margin)*abs(Qj[w]['mdd_p10'])+1e-12 for w in ['P30','P10']]) for i in uniq)
    return out, allp, allpx
for m in [0.1,0.05,0.0]:
    o,a,ax=cnt(m); print('margin',m,o,'pass all G1-G5:',a,'| pass G1-G3 only:',ax)
