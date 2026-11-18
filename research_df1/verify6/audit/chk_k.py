import zipfile, numpy as np, pandas as pd, json
END=pd.Timestamp('1985-12-31')
def kf12():
    z=zipfile.ZipFile('/mnt/project-files/research/broad_etf/data/raw/kf/12_Industry_Portfolios_daily_CSV.zip')
    lines=z.read(z.namelist()[0]).decode('latin1').splitlines()
    rows=[]; sec=0
    for l in lines:
        if 'Value Weighted Returns' in l: sec=1; continue
        if 'Equal Weighted Returns' in l: break
        p=[x.strip() for x in l.split(',')]
        if sec==1 and p[0].isdigit() and len(p[0])==8:
            d=pd.Timestamp(p[0])
            if d>END: continue
            rows.append([d]+[float(x)/100 for x in p[1:13]])
    cols=['date','NoDur','Durbl','Manuf','Enrgy','Chems','BusEq','Telcm','Utils','Shops','Hlth','Money','Other']
    return pd.DataFrame(rows,columns=cols).set_index('date')
def ff():
    z=zipfile.ZipFile('/mnt/project-files/research/broad_etf/data/raw/kf/F-F_Research_Data_Factors_daily_CSV.zip')
    lines=z.read(z.namelist()[0]).decode('latin1').splitlines(); rows=[]
    for l in lines:
        p=[x.strip() for x in l.split(',')]
        if len(p)>=5 and p[0].isdigit() and len(p[0])==8:
            d=pd.Timestamp(p[0])
            if d>END: continue
            rows.append((d,float(p[1])/100,float(p[4])/100))
    return pd.DataFrame(rows,columns=['date','mrf','rf']).set_index('date')
I=kf12(); F=ff()
print('kf12', I.index.min().date(), I.index.max().date(), len(I), 'sat', int((I.index.weekday==5).sum()), 'ff', len(F), 'sat', int((F.index.weekday==5).sum()), 'missing(-99.99)', int((I<=-0.99).sum().sum()))
dly=pd.DataFrame({'DEF3':(I['NoDur']+I['Hlth']+I['Utils'])/3,'STAP':I['NoDur'],'HLTH':I['Hlth'],'UTIL':I['Utils'],'TECH':I['BusEq'],'ENER':I['Enrgy'],'TELE':I['Telcm']})
dly['MKT']=F['mrf']+F['rf']; dly['RF']=F['rf']
dly=dly.dropna()
mo=(1+dly).groupby([dly.index.year,dly.index.month]).prod()-1
mo=mo[(mo.index.get_level_values(0)>=1928)&(mo.index.get_level_values(0)<=1985)]
ex=mo.drop(columns=['RF']).sub(mo['RF'],axis=0)
print('months', len(ex))
def sh(x): return x.mean()/x.std(ddof=1)
yrs=ex.index.get_level_values(0)
K=json.load(open('/mnt/project-files/research/df1/results/df6_k.json'))['sleeves']
rng=np.random.default_rng(7); n=len(ex); nb=int(np.ceil(n/12))
boots=[np.concatenate([np.arange(s0,s0+12) for s0 in rng.integers(0,n-12+1,nb)])[:n] for _ in range(2000)]
for s in ['DEF3','STAP','HLTH','UTIL','TECH','ENER','TELE']:
    ka=sh(ex[s])/sh(ex['MKT']); k1=sh(ex[s][yrs<=1955])/sh(ex['MKT'][yrs<=1955]); k2=sh(ex[s][yrs>=1956])/sh(ex['MKT'][yrs>=1956])
    da=(sh(ex[s])-sh(ex['MKT']))*np.sqrt(12)
    a_s=ex[s].values; a_m=ex['MKT'].values
    kb=np.array([(a_s[ix].mean()/a_s[ix].std(ddof=1))/(a_m[ix].mean()/a_m[ix].std(ddof=1)) for ix in boots])
    p20=np.percentile(kb,20)
    # circular / stationary variant for robustness
    print(s, 'raw-zip k_all %.4f k28_55 %.4f k56_85 %.4f boot20 %.4f k_low %.4f delta %.4f | df6_k: %.4f %.4f %.4f %.4f %.4f %.4f'%(ka,k1,k2,p20,min(ka,k1,k2,p20),da,
        K[s]['MKT']['k_all'],K[s]['MKT']['k_28_55'],K[s]['MKT']['k_56_85'],K[s]['MKT']['k_boot_p20'],K[s]['MKT']['k_low'],K[s]['MKT']['delta_ann_all']))
# variants: no-Saturday (drop Saturdays) to see sensitivity; log vs arithmetic
dl2=dly[dly.index.weekday<5]
mo2=(1+dl2).groupby([dl2.index.year,dl2.index.month]).prod()-1; mo2=mo2[(mo2.index.get_level_values(0)>=1928)]
ex2=mo2.drop(columns=['RF']).sub(mo2['RF'],axis=0)
print('drop-Saturday variant DEF3 k_all %.4f'%(sh(ex2['DEF3'])/sh(ex2['MKT'])))
# daily-based k (for comparison with daily Sharpe used in the 1986-2014 worlds)
dd=dly[(dly.index>=pd.Timestamp('1928-01-01'))]; exd=dd.drop(columns=['RF']).sub(dd['RF'],axis=0)
print('daily-based DEF3 k %.4f'%((exd['DEF3'].mean()/exd['DEF3'].std())/(exd['MKT'].mean()/exd['MKT'].std())))
# annual
yr=(1+dly).groupby(dly.index.year).prod()-1; yr=yr[(yr.index>=1928)]; exy=yr.drop(columns=['RF']).sub(yr['RF'],axis=0)
print('annual-based DEF3 k %.4f'%(sh(exy['DEF3'])/sh(exy['MKT'])))
print('--- daily-frequency variant (not pre-registered) ---')
yd=exd.index.year
for s in ['DEF3']:
    def shd(x): return x.mean()/x.std()
    k_all=shd(exd[s])/shd(exd['MKT']); k1=shd(exd[s][yd<=1955])/shd(exd['MKT'][yd<=1955]); k2=shd(exd[s][yd>=1956])/shd(exd['MKT'][yd>=1956])
    print(s,'daily k_all %.4f k28_55 %.4f k56_85 %.4f'%(k_all,k1,k2))
    # variance ratios month/daily
    for col in [s,'MKT']:
        vd=exd[col].var(); vm=ex[col].var(); nd=len(exd)/len(ex)
        print(col,'VR(monthly/21d) %.3f'%(vm/(nd*vd)), 'lag1 ac daily %.3f'%exd[col].autocorr(1))
