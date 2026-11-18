import zipfile, json, numpy as np, pandas as pd
END=pd.Timestamp('1985-12-31'); CL='/mnt/project-files/research/df5/data/clean/'
FF='/mnt/project-files/research/broad_etf/data/raw/kf/F-F_Research_Data_Factors_daily_CSV.zip'
z=zipfile.ZipFile(FF); nm=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
rows=[]
for ln in z.read(nm).decode('latin1').splitlines():
    p=[x.strip() for x in ln.split(',')]
    if len(p)>=5 and p[0].isdigit() and len(p[0])==8:
        d=pd.Timestamp(p[0])
        if d>END: continue
        rows.append((d,float(p[1])/100,float(p[4])/100))
kf=pd.DataFrame(rows,columns=['d','mrf','rf']).set_index('d'); del rows
mkt=kf['mrf']+kf['rf']
def ld(k):
    s=pd.read_csv(CL+k+'.csv',parse_dates=['date']).set_index('date')['r'].astype(float); return s[s.index<=END]
S={k:ld(k) for k in ['STAP','HLTH','UTIL','TECH','ENER','TELE','MANU','SHOP','FIN']}
rfc=ld('RF')
i3=S['STAP'].index.intersection(S['HLTH'].index).intersection(S['UTIL'].index)
S['DEF3']=(S['STAP'].reindex(i3)+S['HLTH'].reindex(i3)+S['UTIL'].reindex(i3))/3
def mo(s):
    s=s[(s.index>=pd.Timestamp('1928-01-01'))&(s.index<=END)]
    return (1+s).groupby([s.index.year,s.index.month]).prod()-1
M=pd.DataFrame({k:mo(v) for k,v in S.items()}); M['MKT']=mo(mkt); M['RFkf']=mo(kf['rf']); M['RFcl']=mo(rfc)
print('months',len(M),M.index[0],M.index[-1],'nan',int(M.isna().sum().sum()))
print('RF kf vs clean max abs monthly diff',float((M['RFkf']-M['RFcl']).abs().max()))
# check calendar: do sleeves have Saturday rows pre-1952? KF market?
for k in ['STAP','DEF3']:
    s=S[k]; print(k,'saturday rows pre-1953',int(((s.index.weekday==5)&(s.index.year<1953)).sum()))
print('KF mkt saturday rows pre-1953',int(((mkt.index.weekday==5)&(mkt.index.year<1953)).sum()))
def sh(x): return x.mean()/x.std(ddof=1)
out={}
yrs=M.index.get_level_values(0)
ref=json.load(open('/mnt/project-files/research/df1/results/df6_k.json'))['sleeves']
rng=np.random.default_rng(12345); n=len(M); nb=int(np.ceil(n/12))
B=[np.concatenate([np.arange(s0,s0+12) for s0 in rng.integers(0,n-12+1,nb)])[:n] for _ in range(2000)]
for rfname in ['RFkf','RFcl']:
    ex=M.drop(columns=['RFkf','RFcl']).sub(M[rfname],axis=0)
    print('== RF source',rfname)
    for s in ['DEF3','STAP','HLTH','UTIL','TECH','ENER','TELE']:
        r={}
        for tag,sel in (('all',np.ones(n,bool)),('28_55',yrs<=1955),('56_85',yrs>=1956)):
            e=ex[sel]; r['k_'+tag]=sh(e[s])/sh(e['MKT']); r['dA_'+tag]=(sh(e[s])-sh(e['MKT']))*np.sqrt(12)
        a=ex[s].values; m=ex['MKT'].values
        kb=np.array([(a[ix].mean()/a[ix].std(ddof=1))/(m[ix].mean()/m[ix].std(ddof=1)) for ix in B])
        r['p20']=np.percentile(kb,20); r['low']=min(r['k_all'],r['p20'],r['k_28_55'],r['k_56_85'])
        rr=ref[s]['MKT']
        print('%-5s k_all %.4f (ref %.4f) 28_55 %.4f (%.4f) 56_85 %.4f (%.4f) p20 %.4f (%.4f) low %.4f (%.4f) dAnn %.4f (%.4f)'%(
            s,r['k_all'],rr['k_all'],r['k_28_55'],rr['k_28_55'],r['k_56_85'],rr['k_56_85'],r['p20'],rr['k_boot_p20'],r['low'],rr['k_low'],r['dA_all'],rr['delta_ann_all']))
        out[(rfname,s)]=r
# Saturday-free variant: compound on weekday-only? (sensitivity: drop Saturday rows entirely)
print('== sensitivity: market Sharpe annual', float(sh(M['MKT']-M['RFkf'])*np.sqrt(12)),'DEF3', float(sh(M['DEF3']-M['RFkf'])*np.sqrt(12)))
