"""Independent rough cross-check of LMX1 (no shared engine loop): daily-rebalanced overlay on the v1 after-tax curve, sleeve untaxed."""
import sys, numpy as np
sys.path.insert(0,'/mnt/project-files/research/lmx1/code'); sys.path.insert(0,'/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import lmx, ii, el
for bn in ['real_ndx_86_14','real_spx_55_85','real_spx_70_85']:
    fin0,E0=lmx.run(bn,[0,0],'R'); A,B=lmx.sleeves(bn); S=A[0,:,0]
    TQ,DEP,CU,IDL=ii.ref_in(bn); rf=np.asarray(el.ctx(bn)['rf'])[0,ii.WARM:]
    r1=np.r_[0,E0[0,1:]/E0[0,:-1]-1]; yrs=len(r1)/252
    Lp=np.r_[CU[0,0],CU[0,:-1]]; g=Lp/3
    for mode in ('U','R'):
        F = rf+0.004/252 if mode=='U' else 2.5*g*(rf+3*0.004/252-0.0245/252)+2.5*(1-g)*DEP[0]
        F2=lmx.fin_rate(bn,mode)[0]; assert np.allclose(F,F2), 'fin mismatch'
        for w in (0.2,0.3):
            x=r1+w*(S-F); x[0]=0
            c_new=np.prod(1+x)**(1/yrs)-1; c0=np.prod(1+r1)**(1/yrs)-1
            print(bn,mode,'w',w,'approx d %+.4f'%(c_new-c0),'| sleeve ann mean %.4f fin ann mean %.4f rf %.4f on-share %.2f corr(v1,sleeve) %.2f'%(S.mean()*252,F.mean()*252,rf.mean()*252,(Lp>=2.5).mean(),np.corrcoef(r1[1:],S[1:])[0,1]))
