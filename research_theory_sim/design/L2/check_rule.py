import numpy as np, time, rule, harness as H, sim
d=sim.simulate(300,7860,7,True); close=np.cumprod(1+d['r'],axis=1)*37.0
q=dict(hv=140,H=1.5,a0=0.03,a1=0.2,a2=0.0,a3=1.0,Hr=5.0,use_y10=0)
A=H.family(close,d['rf'],None,q); B=rule.target_levels(close,d['rf'])
print('max |harness-rule| =',np.nanmax(np.abs(A-B)), 'nan pattern equal:',np.array_equal(np.isnan(A),np.isnan(B)))
C=rule.target_levels(close*1234.5,d['rf']); print('scale invariance max diff',np.nanmax(np.abs(C-B)))
# causality: perturb columns > t0 and check columns <= t0 unchanged
t0=4000; c2=close.copy(); c2[:,t0+1:]*=np.exp(np.random.default_rng(0).normal(0,0.05,(300,7860-t0-1))).cumprod(axis=1)
r2=d['rf'].copy(); r2[:,t0+1:]+=0.0003
D=rule.target_levels(c2,r2); print('causality: max diff cols<=t0',np.nanmax(np.abs(D[:,:t0+1]-B[:,:t0+1])))
# NaN robustness
c3=close.copy(); c3[:5,:50]=np.nan; c3[10,1000:1010]=np.nan; r3=d['rf'].copy(); r3[20,2000:2030]=np.nan
E=rule.target_levels(c3,r3); print('nan input: finite share',np.isfinite(E[:,300:]).mean(),'range',np.nanmin(E),np.nanmax(E))
print('1-D input ok:',rule.target_levels(close[0],d['rf'][0]).shape)
# speed
g=np.random.default_rng(1); P,T=500,10000
cl=np.exp(np.cumsum(g.normal(0.0003,0.012,(P,T)),axis=1)); rf=np.full((P,T),0.03/252)
t=time.time(); X=rule.target_levels(cl,rf); print('speed P=500,T=10000: %.2fs'%(time.time()-t), X.dtype, X.shape)
