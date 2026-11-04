import json,io,lzma,numpy as np,pandas as pd
R='/mnt/project-files/research/'
H=json.load(open(R+'giant_trend/results2/holdings.json'))
CM=json.load(open(R+'giant_trend/results2/cusip_map.json'))
z=np.load(io.BytesIO(lzma.open(R+'data/us_stocks/sp500_le2014_v3.npz.xz').read()),allow_pickle=True)
dates=pd.to_datetime(z['dates'],unit='D');T=len(dates)
adj=z['adj'].astype(float);divy=np.nan_to_num(z['divy'].astype(float))
mem=np.unpackbits(z['member'],axis=0)[:T].astype(bool);N=adj.shape[1]
fin=np.isfinite(adj)
# returns
pf=pd.DataFrame(adj).ffill().values
ret=np.zeros((T,N))
with np.errstate(all='ignore'):
    ret[1:]=pf[1:]/pf[:-1]-1
ret=np.nan_to_num(ret,nan=0.0,posinf=0.0,neginf=0.0)
ret-=0.154*divy
first=np.array([np.argmax(fin[:,j]) if fin[:,j].any() else T for j in range(N)])
for j in range(N):
    ret[:first[j]+1,j]=0  # 0 before first price (incl. first day)
    if fin[:,j].any():
        last=np.where(fin[:,j])[0][-1]
        if last<T-1-5:
            k=max(last-250,0)
            r250=pf[last,j]/pf[k,j]-1
            ret[last+1:,j]=0
            ret[last+1,j]=-0.5 if r250<-0.3 else 0.0
tb=pd.read_csv(R+'data/deep_history/clean/TBILL_daily_1927_2014.csv',parse_dates=['date']).set_index('date')['rate_known_pct']
rf=tb.reindex(dates,method='ffill').fillna(0).values/100  # annual
cashr=np.maximum(rf-0.02,0)*0.846/252
rfd=rf/252
# filings
def dec_idx(f):
    i=int(np.searchsorted(dates.values,np.datetime64(f)));return i+2
F={}
for x in H:
    d=dec_idx(x['filed'])
    if d>=T: continue
    hold={}
    for c,(v,nm,sh) in x['hold'].items():
        if c in CM: hold[CM[c]]=hold.get(CM[c],0)+v
    F.setdefault(x['giant'],[]).append((x['filed'],x['period'],d,hold))
for g in F: F[g].sort(key=lambda a:(a[0],a[1]))
decdays=sorted({f[2] for g in F for f in F[g]})
def c3_target(t,giants=None):
    S=set()
    for g,L in F.items():
        if giants and g not in giants: continue
        cur=[f for f in L if f[2]<=t]
        if not cur: continue
        f=cur[-1]
        if t-f[2]>200: continue
        h=[(v,j) for j,v in f[3].items() if mem[t,j] and fin[t,j]]
        h.sort(key=lambda a:-a[0])
        S|={j for v,j in h[:5]}
    return sorted(S)
def ew_target(t): return list(np.where(mem[t]&fin[t])[0])
qfirst=set()
for i in range(1,T):
    if dates[i].quarter!=dates[i-1].quarter or dates[i].year!=dates[i-1].year: qfirst.add(i)
C=0.003;TAXR=0.22
def run(s,e,kind,target_fn):
    val=np.zeros(N);basis=np.zeros(N);cash=1.0;gains=0.0;taxpaid=0
    pre=[1.0];wealth=[1.0]
    def rebal(t,tg):
        nonlocal cash,gains
        V=val.sum()+cash
        w=np.zeros(N)
        if tg: w[tg]=1.0/len(tg)
        scale=1.0
        for _ in range(30):
            tv=w*V*scale
            tr=np.abs(tv-val).sum()
            cost=C*tr
            scale=(V-cost)/V if tg else 1.0
            if not tg: break
        tv=w*V*scale
        # sells
        sell=np.maximum(val-tv,0);buy=np.maximum(tv-val,0)
        with np.errstate(all='ignore'):
            frac=np.where(val>0,sell/val,0)
        proceeds=sell*(1-C)
        gains+=(proceeds-basis*frac).sum()
        basis[:]=basis-basis*frac
        basis[:]=basis+buy*(1+C)
        val[:]=tv
        cash=V-tv.sum()-C*(sell.sum()+buy.sum())
        if cash<0 and cash>-1e-9: cash=0
    def taxit(t,final=False):
        nonlocal gains,cash,val,basis,taxpaid
        tax=max(0,TAXR*(gains-0.25));gains=0.0
        if tax>0:
            tot=val.sum()+cash
            f=max(1-tax/tot,0)
            val*=f;basis*=f;cash*=f;taxpaid+=tax
    rebal(s,target_fn(s))
    for t in range(s+1,e+1):
        v0=val.sum()+cash
        val*=1+ret[t];cash*=1+cashr[t]
        v1=val.sum()+cash
        pre.append(pre[-1]*v1/v0)
        if kind=='c3' and t in decset: rebal(t,target_fn(t))
        if kind=='ew' and t in qfirst: rebal(t,target_fn(t))
        if t==e:
            rebal(t,[])
        if t==e or dates[t].year!=dates[min(t+1,T-1)].year: taxit(t)
        wealth.append(val.sum()+cash)
    return np.array(pre),np.array(wealth)
decset=set(decdays)
def stats(pre,w,s,e):
    r=pre[1:]/pre[:-1]-1;ex=r-rfd[s+1:e+1]
    sr=ex.mean()/ex.std(ddof=1)*np.sqrt(252)
    yrs=(dates[e]-dates[s]).days/365.25
    dd=lambda x:float((x/np.maximum.accumulate(x)-1).min())
    return dict(cagr_at=float(w[-1]**(1/yrs)-1),sharpe=float(sr),maxdd_pre=dd(pre),maxdd_at=dd(w),final_at=float(w[-1]),cagr_pre=float(pre[-1]**(1/yrs)-1))
def idx_ge(d): return int(np.searchsorted(dates.values,np.datetime64(d)))
def idx_le(d): return int(np.searchsorted(dates.values,np.datetime64(d),side='right'))-1
per={'FULL':('1999-05-20','2014-12-31'),'H1':('1999-05-20','2006-12-31'),'H2':('2007-01-01','2014-12-31')}
out={}
for nm,(a,b) in per.items():
    s,e=idx_ge(a),idx_le(b)
    for k,fn,kind in [('C3',c3_target,'c3'),('EW',ew_target,'ew'),('BRK_C3',lambda t:c3_target(t,{'BRK'}),'c3')]:
        if k=='BRK_C3': continue
        out[f'{k}_{nm}']=stats(*run(s,e,kind,fn),s,e)
for k,v in out.items(): print(k,{a:round(b,4) for a,b in v.items()})
json.dump(out,open(R+'giant_trend/verify2/verify2.json','w'),indent=1)
