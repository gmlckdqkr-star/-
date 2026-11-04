import pandas as pd, numpy as np, json, io, warnings
warnings.filterwarnings('ignore')
KF='/mnt/project-files/research/data/ken_french/raw/mirror_a91quaini/'
def kf(fn):
    rows=[];hdr=None
    for ln in open(KF+fn,encoding='latin1'):
        p=[x.strip() for x in ln.strip().split(',')]
        if hdr is None:
            if p[0]=='Date' or (len(p)>2 and p[0]=='' and 'Food' in ln): hdr=['Date']+p[1:]
            continue
        if len(p[0])==6 and p[0].isdigit(): rows.append(p)
        elif rows: break
    d=pd.DataFrame(rows,columns=hdr[:len(rows[0])]);d.index=d['Date'].astype(int);d=d.drop(columns='Date').astype(float)
    return d.replace(-99.99,np.nan)/100
ind=kf('17_Industry_Portfolios.CSV'); ff=kf('F-F_Research_Data_Factors.CSV')
op=kf('25_Portfolios_ME_OP_5x5.CSV')['BIG HiOP']; pr=kf('25_Portfolios_ME_Prior_12_2.CSV')['BIG HiPRIOR']
cut=201412
ind=ind[ind.index<=cut]; ff=ff[ff.index<=cut]
mkt=ff['Mkt-RF']+ff['RF']; rf=ff['RF']
sh=pd.read_excel('/mnt/project-files/research/data/macro_regime/raw/SHILLER_ie_data_IA_20141222172333.xls',sheet_name='Data',header=None,skiprows=8,engine='xlrd')
sh=sh.iloc[:,[0,1,2]].dropna();sh.columns=['d','P','D']
sh['d']=sh['d'].astype(float);sh['ym']=(sh.d.astype(int)*100+np.round((sh.d-sh.d.astype(int))*100+1e-6).astype(int))
sh=sh.set_index('ym');dp=(sh.D.astype(float)/sh.P.astype(float))
idx=ind.index[ind.index>=192607]
months=list(idx)
R={c:ind[c].reindex(idx) for c in ind.columns}
R['MKT']=mkt.reindex(idx);R['OP']=op.reindex(idx);R['PR']=pr.reindex(idx)
EXTRA={'OP':0.0015,'PR':0.025}
assert all(R[k].loc[196307:].isna().sum()==0 for k in ['MKT','OP','PR']), 'missing'
assert ind.loc[192701:].isna().sum().sum()==0
pos={m:i for i,m in enumerate(months)}
# membership schedules
R60=ind.reindex(idx).add(1).rolling(60).apply(np.prod,raw=True)-1
def sched(kind):
    mem={};cur=None
    for m in months:
        if m%100!=12 or np.isnan(R60.loc[m]).any(): mem[m]=cur;continue
        rk=R60.loc[m].sort_values(ascending=False);names=list(rk.index)
        if kind=='MUN':
            if cur is None or ((pos[m]-pos[first[0]])%60==0):
                if cur is None: first[0]=m
                top=names[:3];keep=[c for c in cur if c in top] if cur else []
                new=keep+[c for c in top if c not in keep];cur=new
        else:
            if cur is None: cur=names[:3]
            else:
                keep=[c for c in cur if names.index(c)<6]
                for c in names:
                    if len(keep)>=3:break
                    if c not in keep: keep.append(c)
                cur=keep
        mem[m]=list(cur)
    return mem
first=[None];MUN=sched('MUN');first=[None];BUF=sched('BUF')
FEE=0.003
def run(strategy,s,e,tax=True):
    H={};gains=[0.0];cash=[0.0];W=[1.0]
    def val():return sum(v[0] for v in H.values())
    def sell(a,amt):
        v,b=H[a];amt=min(amt,v);bp=b*amt/v if v>0 else 0
        gains[0]+=amt*(1-FEE)-bp;H[a]=[v-amt,b-bp];cash[0]+=amt*(1-FEE)
        if H[a][0]<1e-15:del H[a]
    def buy(a,c):
        amt=c/(1+FEE);x=H.get(a,[0,0]);H[a]=[x[0]+amt,x[1]+amt]
    def reb(w):  # target weights, exact fee
        Wt=val()+cash[0];f=0
        for _ in range(60):
            tg={a:w.get(a,0)*(Wt-f) for a in set(w)|set(H)}
            f=FEE*sum(abs(tg[a]-H.get(a,[0])[0]) for a in tg)
        tg={a:w.get(a,0)*(Wt-f) for a in set(w)|set(H)}
        for a in tg:
            d=H.get(a,[0])[0]-tg[a]
            if d>1e-14:sell(a,d)
        need={a:tg[a]-H.get(a,[0])[0] for a in tg if tg[a]-H.get(a,[0])[0]>1e-14};tot=sum(need.values())
        c=cash[0]
        for a,n in need.items():buy(a,c*n/tot)
        cash[0]=0
    def apply_month(m):
        d=0.15*dp.get(m,0)/12
        for a in list(H):
            r=R[a].loc[m]
            if np.isnan(r):raise Exception('nan '+a)
            H[a][0]*=1+r-0.002/12-d-EXTRA.get(a,0)/12
    def target(t):  # weights/members decided at end of month t
        if strategy=='MKT':return {'MKT':1.0}
        if strategy in('MUN','BUF'):
            mem=(MUN if strategy=='MUN' else BUF)[t]
            return {'MKT':1.0} if mem is None else mem
        if strategy=='FIS':
            return {'OP':.5,'PR':.5} if t>=196307 else {'MKT':1.0}
    def taxpay():
        if not tax:return
        t=0.22*max(gains[0]-0.25,0);gains[0]=0
        if t>0:
            V=val()
            for a in H:H[a][0]*=1-t/V
    i0=pos[s];prev=months[i0-1]
    path=[];yrs=0
    tg=target(prev);cash[0]=1.0
    if isinstance(tg,dict):reb(tg);cur=tg
    else:
        reb({a:1/len(tg) for a in tg});cur=list(tg)
    g0=gains[0];gains[0]=0  # initial buy no gain
    for i in range(i0,pos[e]+1):
        m=months[i];apply_month(m)
        last=(m==e)
        if not last:
            tg=target(m)
            if isinstance(tg,dict):
                if strategy=='FIS' or set(tg)!=(set(cur) if isinstance(cur,dict) else None): reb(tg)
                cur=tg
            else:
                if set(tg)!=set(cur if isinstance(cur,list) else []):
                    if isinstance(cur,dict):
                        for a in list(H):sell(a,H[a][0])
                        c=cash[0];cash[0]=0
                        for a in tg:buy(a,c/len(tg))
                    else:
                        for a in [x for x in cur if x not in tg]:sell(a,H[a][0])
                        new=[x for x in tg if x not in cur];c=cash[0];cash[0]=0
                        for a in new:buy(a,c/len(new))
                cur=list(tg)
        path.append(val()+cash[0])
        if m%100==12 and not last:taxpay()
        if last:
            for a in list(H):sell(a,H[a][0])
            fin=cash[0];cash[0]=0
            if tax:
                t=0.22*max(gains[0]-0.25,0);fin-=t
            n=len(path)
    return np.array(path),fin,n
def stats(strategy,s,e):
    pt,_,n=run(strategy,s,e,tax=False)
    pa,fin,n=run(strategy,s,e,tax=True)
    w=np.r_[1.0,pt];ret=w[1:]/w[:-1]-1
    ex=ret-rf.reindex(months[pos[s]:pos[e]+1]).values
    sr=ex.mean()/ex.std(ddof=1)*np.sqrt(12)
    def mdd(x):
        x=np.r_[1,x];return float((x/np.maximum.accumulate(x)-1).min())
    cg=fin**(12/n)-1
    # pretax-liquidation CAGR for reference
    return dict(cagr_after_tax=cg,final_wealth=fin,sharpe=sr,mdd_pretax=mdd(pt),mdd_aftertax=mdd(pa),pretax_cagr_noliq=float(pt[-1]**(12/n)-1),months=n)
out={}
E1=(192701,196912);E2=(197001,201412);F1=(196401,198512);F2=(198601,201412)
for st in ['MKT','MUN','BUF']:
    for nm,(s,e) in [('1927-69',E1),('1970-2014',E2)]:
        out[f'{st}/{nm}']=stats(st,s,e)
for nm,(s,e) in [('1964-85',F1),('1986-2014',F2)]:
    out[f'FIS/{nm}']=stats('FIS',s,e)
json.dump(out,open('/mnt/project-files/research/giant_trend/verify/verify_r1.json','w'),indent=1)
for k,v in out.items():print(k,{a:round(b,4) for a,b in v.items()})
print(MUN[196612],MUN[196912],BUF[196912],MUN[201412],BUF[201412])
