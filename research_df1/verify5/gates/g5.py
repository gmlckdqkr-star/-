import numpy as np, pickle
z=np.load('/tmp/df5w/df5_arr.npz')
for w in ['X30','X10']:
    R=pickle.load(open('/tmp/df5v/gates/R_%s.pkl'%w,'rb'))
    qc,qm=z['QQQ||'+w].astype(np.float64)
    print(w)
    for thr in [-0.3,-0.35,-0.4,-0.5]:
        qp=np.mean(qm<thr); n=0; ex=[]
        for r in R:
            c,m=z[r[0]+'||'+w].astype(np.float64)
            if r[1]>0 and np.mean(m<thr)<=qp: n+=1; ex.append((r[0],round(r[1]*100,2),np.mean(m<thr)))
        print('  thr %.2f QQQ P=%.3f  n(pair>0 & P<=QQQ)=%d' % (thr,qp,n), ex[:10])
    for r in R:
        if r[1]>0 and r[5]>0: print('  pair>0 & paired-med MDD better:', r[0], r[1]*100, r[5]*100)
    for r in R:
        if r[0]=='A3|e1.00|c0.20|GOLD+LTT+DEF3|none': print('  A3 closest exact: pair %.6f ddp10 %.6f' % (r[1], r[2]))
