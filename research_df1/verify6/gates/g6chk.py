import numpy as np, pandas as pd
END=pd.Timestamp('1985-12-31'); CL='/mnt/project-files/research/df5/data/clean/'
def ld(k):
    s=pd.read_csv(CL+k+'.csv',parse_dates=['date']).set_index('date')['r'].astype(float); return s[s.index<=END]
S={k:ld(k) for k in ['STAP','HLTH','UTIL','TECH','RF']}
i3=S['STAP'].index.intersection(S['HLTH'].index).intersection(S['UTIL'].index)
S['DEF3']=(S['STAP'].reindex(i3)+S['HLTH'].reindex(i3)+S['UTIL'].reindex(i3))/3
cal=S['TECH'].index[(S['TECH'].index>=pd.Timestamp('1928-01-03'))&(S['TECH'].index.weekday<5)]
def wk(s):
    pos=cal.searchsorted(s.index); ok=pos<len(cal); s2=s[ok]; tgt=cal[pos[ok]]
    return (1+s2).groupby(tgt).prod().reindex(cal).fillna(1.0).values-1
tech,def3,rf=wk(S['TECH']),wk(S['DEF3']),wk(S['RF'])
print('cal',len(cal),cal[0].date(),cal[-1].date(), 'start eval', cal[300].date())
W=300
core=tech-0.002/252
lev=3*(tech-0.02/252)-2*rf-0.0245/252
slv=def3-0.0015/252
def sim(ws,assets,reb,cost=0.003):
    v=np.array(ws,float); E=[1.0]; k=0
    for t in range(W+1,len(cal)):
        k+=1
        v=v*(1+np.array([a[t] for a in assets]))
        if reb and k%reb==0:
            tot=v.sum(); tg=np.array(ws)*tot; tc=cost*np.abs(tg-v).sum(); v=tg*(tot-tc)/tot
        E.append(v.sum())
    E=np.array(E); mdd=(E/np.maximum.accumulate(E)-1).min(); cg=E[-1]**(252/(len(E)-1))-1
    return cg,mdd
# core gross of dividends (core total return = tech - 0.002/252, dividend tax ignored here)
cgc,mc=sim([1.0],[core],0)
cgm,mm=sim([0.2,0.0,0.8],[lev,core,slv],252)
print('pre-tax approx  core cagr %.4f mdd %.4f | top mix cagr %.4f mdd %.4f | ddm %.4f'%(cgc,mc,cgm,mm,1-abs(mm)/abs(mc)))
# components drawdown
for nm,a in (('DEF3',slv),('TECH core',core),('3x lev',lev)):
    print(nm,'cagr %.4f mdd %.4f'%sim([1.0],[a],0))
# MDD window of the mix
