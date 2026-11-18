import os, sys, ast, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR']='/tmp/df5v/gates/nb'
for p in ('c3_relax','c3_invent','c3_combo'): sys.path.insert(0,'/mnt/project-files/research/%s/code'%p)
import jp, iv
END=pd.Timestamp('2014-12-31')
a,b,P,blk,seed=iv.POOLS['dev250']; print('pool',a,b,P,blk,seed)
R,M=jp.calendar(a,b); X=jp.mkX(R,M,'NDX'); del R,M
assert X.index.max()<=END and X.index.min()>=pd.Timestamp('1986-01-01')
print('X rows',len(X), X.index.min().date(), X.index.max().date(), 'nan r', int(X['r'].isna().sum()), 'zero r', int((X['r']==0).sum()))
# exec df5lib._xworld source in isolation
src=open('/mnt/project-files/research/df1/code/df5lib.py').read(); tree=ast.parse(src)
fn=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_xworld'][0]
ns=dict(np=np,pd=pd,BLK=250,W=300); exec(compile(ast.Module([fn],[]),'x','exec'),ns)
ii,nstarts=ns['_xworld'](X,500); print('df5lib._xworld: starts',nstarts,'ii',ii.shape)
# my own reimplementation
lv=np.cumprod(1+X['r'].fillna(0).values); D=X.index; n=len(X)
pos=lambda d:int(D.searchsorted(pd.Timestamp(d)))
tr1=pos('1987-10-01')+int(np.argmin(lv[pos('1987-10-01'):pos('1988-01-01')])); pk1=pos('1987-01-01')+int(np.argmax(lv[pos('1987-01-01'):tr1+1]))
pk2=pos('2000-01-01')+int(np.argmax(lv[pos('2000-01-01'):pos('2001-01-01')])); tr2=pk2+int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3=pos('2007-01-01')+int(np.argmax(lv[pos('2007-01-01'):pos('2008-07-01')])); tr3=pos('2008-07-01')+int(np.argmin(lv[pos('2008-07-01'):pos('2009-07-01')]))
excl=np.zeros(n,bool)
for nm,p_,t_ in (('1987',pk1,tr1),('2000-02',pk2,tr2),('2007-09',pk3,tr3)):
    e=min(t_+250,n-1); excl[p_:e+1]=True
    print('%-8s peak %s  trough %s  depth %.1f%%  excl_end %s  (excl days %d)'%(nm,D[p_].date(),D[t_].date(),100*(lv[t_]/lv[p_]-1),D[e].date(),e-p_+1))
# true global peak check: is pk1 the actual pre-crash peak? check running max before the windows
for nm,p_ in (('1987',pk1),('2000',pk2),('2007',pk3)):
    rm=np.max(lv[:p_+1]); print('  %s peak is all-time high so far: %s ; lv/prev max %.4f'%(nm, lv[p_]>=rm-1e-12, lv[p_]/rm))
# recovery to prior peak date
for nm,p_,t_ in (('1987',pk1,tr1),('2000-02',pk2,tr2),('2007-09',pk3,tr3)):
    j=t_
    while j<n and lv[j]<lv[p_]: j+=1
    print('  %s recovered to peak: %s'%(nm, D[j].date() if j<n else 'not by 2014-12-31'))
starts=np.array([s for s in range(1,n-250) if not excl[s:s+250].any()])
print('my starts',len(starts),'| P-world starts (range 1..n-250)', n-251, '| fraction of start points excluded %.3f'%(1-len(starts)/(n-251)))
print('excluded days',int(excl.sum()),'of',n,'= %.3f'%(excl.mean()))
# days that can never appear: excl days plus? (days in segments shorter than 250 between exclusions)
cover=np.zeros(n,bool)
for s in starts: cover[s:s+250]=True
print('days reachable by some X block: %d (%.3f); non-excluded days unreachable: %d'%(cover.sum(),cover.mean(),int((~excl & ~cover).sum())))
print('unreachable non-excl days:', [(str(D[i].date())) for i in np.where(~excl & ~cover)[0][:5]], '...')
segs=[];i=0
while i<n:
    if not excl[i]:
        j=i
        while j<n and not excl[j]: j+=1
        segs.append((str(D[i].date()),str(D[j-1].date()),j-i)); i=j
    else: i+=1
print('kept segments', segs)
# Compare ii identical
g=np.random.default_rng(7); T=300+30*252; nb=T//250+1; st=starts[g.integers(0,len(starts),(500,nb))]
ii2=(st[:,:,None]+np.arange(250)[None,None,:]).reshape(500,-1)[:,:T]
print('ii identical to df5lib:', np.array_equal(ii,ii2), 'any excluded day in ii:', bool(excl[ii].any()))
# sampling weights: share of path days (post-warmup) by year, X vs P
ov_ii=None
sys.path.insert(0,'/mnt/project-files/research/crash_overlay/code')
gP=np.random.default_rng(7); stP=gP.integers(1,n-250,(500,nb)); iiP=(stP[:,:,None]+np.arange(250)[None,None,:]).reshape(500,-1)[:,:T]
yrs=D.year.values
sx=pd.Series(yrs[ii[:,300:]].ravel()).value_counts(normalize=True).sort_index()
sp=pd.Series(yrs[iiP[:,300:]].ravel()).value_counts(normalize=True).sort_index()
src=pd.Series(yrs).value_counts(normalize=True).sort_index()
tab=pd.DataFrame({'src':src,'P':sp,'X':sx}).fillna(0)
ar=X['r'].groupby(D.year).apply(lambda r: np.prod(1+r)-1)
tab['ndx_yr_ret']=ar
print((tab*100).round(2).to_string())
# mean daily NDX return in source, P sampled, X sampled
r=X['r'].fillna(0).values
print('mean daily r *252: source %.4f | P sampled %.4f | X sampled %.4f | non-excl days %.4f | excl days %.4f'%(r.mean()*252, r[iiP[:,300:]].mean()*252, r[ii[:,300:]].mean()*252, r[~excl].mean()*252, r[excl].mean()*252))
print('daily vol *sqrt252: source %.4f | X sampled %.4f'%(r.std()*np.sqrt(252), r[ii[:,300:]].std()*np.sqrt(252)))
# Grouped shares: 1995-03..2000-03 bubble run-up
bub=(D>=pd.Timestamp('1995-01-01'))&(D<pd.Timestamp('2000-03-11'))
print('share of path days from 1995-01..2000-03-10 bubble: source %.3f P %.3f X %.3f'%(bub.mean(), bub[iiP[:,300:]].mean(), bub[ii[:,300:]].mean()))
np.save('/tmp/df5v/gates/iiX.npy',ii); np.save('/tmp/df5v/gates/excl.npy',excl)
# Remaining drawdowns within kept segments (calendar, real history, not paths)
def dds(lo,hi,thr=-0.15):
    seg=lv[lo:hi+1]; out=[]; pk=0; i=0; m=len(seg)
    rm=np.maximum.accumulate(seg); dd=seg/rm-1
    i=0
    while i<m:
        if dd[i]<thr:
            j=i
            while j<m and dd[j]<0: j+=1
            k=i+int(np.argmin(dd[i:j])); p=int(np.argmax(seg[:k+1]))  # peak = running max index
            p=k-int(np.argmax(seg[k::-1]>=rm[k]-1e-12))
            out.append((str(D[lo+p].date()),str(D[lo+k].date()),round(100*dd[k],1),'recovered' if j<m else 'not recovered in segment'))
            i=j
        else: i+=1
    return out
kept=np.where(~excl)[0]
for s0,s1,L in segs:
    lo=pos(s0); hi=pos(s1)
    print('segment',s0,s1,'drawdowns < -15%:',dds(lo,hi))
# max DD within a single 250-day block anywhere among allowed starts
mdd_blk=[]
for s in starts:
    seg=lv[s:s+250]; mdd_blk.append(np.min(seg/np.maximum.accumulate(seg)-1))
mdd_blk=np.array(mdd_blk); w=np.argsort(mdd_blk)[:5]
print('worst intra-block DD among allowed starts:', [(str(D[starts[k]].date()), round(100*mdd_blk[k],1)) for k in w])
