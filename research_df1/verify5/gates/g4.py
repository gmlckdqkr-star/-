import numpy as np, json, pickle
D=json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
rows=D['rows']; Qj=D['qqq']
z=np.load('/tmp/df5w/df5_arr.npz')
uniq,dups=pickle.load(open('/tmp/df5v/gates/uniq.pkl','rb'))
for w in ['X30','X10','P30','P10']:
    qa=z['QQQ||'+w].astype(np.float64); qc,qm=qa
    qp10=np.percentile(qm,10); qmed=np.median(qm); qp50=np.mean(qm< -0.5)
    print('\n=== %s  QQQ: cagr med %.4f p10 %.4f | MDD p10 %.4f med %.4f p90 %.4f | P(MDD<-50%%)=%.3f P(MDD<-40%%)=%.3f' % (w, np.median(qc), np.percentile(qc,10), qp10, qmed, np.percentile(qm,90), qp50, np.mean(qm<-0.4)))
    R=[]
    for i in uniq:
        c,m=z[i+'||'+w].astype(np.float64)
        pair=np.median(c-qc); ddp10=1-abs(np.percentile(m,10))/abs(qp10); ddmed=1-abs(np.median(m))/abs(qmed)
        p50=np.mean(m<-0.5); 
        # paired MDD: median of per-path (|mdd_q| - |mdd_c|)
        pmdd=np.median(np.abs(qm)-np.abs(m))
        R.append((i,pair,ddp10,ddmed,p50,pmdd,np.median(c)-np.median(qc),np.percentile(c,10)-np.percentile(qc,10)))
    pair=np.array([r[1] for r in R]); ddp=np.array([r[2] for r in R]); ddm=np.array([r[3] for r in R]); p50=np.array([r[4] for r in R]); pmdd=np.array([r[5] for r in R])
    for mg in [0,0.05,0.10]:
        print(' margin %.2f: pair>0 & p10MDD shallower: %d | pair>0 & medMDD shallower: %d' % (mg, np.sum((pair>0)&(ddp>=mg-1e-12)), np.sum((pair>0)&(ddm>=mg-1e-12))))
    print(' pair>0 & P(MDD<-50%%) <= QQQ: %d ; pair>0 & paired-median MDD improvement>0: %d' % (np.sum((pair>0)&(p50<=qp50)), np.sum((pair>0)&(pmdd>0))))
    print(' pair>=0 & ddp10>=0 (weak): %d; pair>-0.001 & ddp10>0: %d' % (np.sum((pair>=0)&(ddp>=0)), np.sum((pair>-0.001)&(ddp>0))))
    if w in ('X30','X10'):
        # closeness: distance to corner in (pair pp, ddp10 %) space: shortfall
        sf=np.sqrt(np.minimum(pair*100,0)**2 + np.minimum(ddp*100,0)**2)  # shortfall pp and % 
        o=np.argsort(sf)
        print(' 5 closest to both-better corner (p10 MDD), shortfall=sqrt(min(pair_pp,0)^2+min(dd%,0)^2):')
        for k in o[:8]: r=R[k]; print('   %-45s pair %+6.2fpp  p10MDD %+6.1f%% shallower  medMDD %+6.1f%%  P(<-50)=%.3f  med %+.2fpp p10cagr %+.2fpp' % (r[0], r[1]*100, r[2]*100, r[3]*100, r[4], r[6]*100, r[7]*100))
        sf2=np.sqrt(np.minimum(pair*100,0)**2 + np.minimum(ddm*100,0)**2); o=np.argsort(sf2)
        print(' 5 closest (median MDD):')
        for k in o[:5]: r=R[k]; print('   %-45s pair %+6.2fpp  medMDD %+6.1f%%  p10MDD %+6.1f%%' % (r[0], r[1]*100, r[3]*100, r[2]*100))
        # pareto front pair vs ddp10
        idx=np.argsort(-pair); best=-9; front=[]
        for k in idx:
            if ddp[k]>best: best=ddp[k]; front.append(k)
        print(' Pareto front (pair desc, p10MDD margin):')
        for k in front[:25]: r=R[k]; print('   %-45s pair %+6.2fpp  p10MDD %+6.1f%%' % (r[0], r[1]*100, r[2]*100))
    pickle.dump(R,open('/tmp/df5v/gates/R_%s.pkl'%w,'wb'))
