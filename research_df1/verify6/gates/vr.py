import zipfile, numpy as np, pandas as pd
END=pd.Timestamp('2014-12-31'); CL='/mnt/project-files/research/df5/data/clean/'
FF='/mnt/project-files/research/broad_etf/data/raw/kf/F-F_Research_Data_Factors_daily_CSV.zip'
z=zipfile.ZipFile(FF); nm=[n for n in z.namelist() if n.lower().endswith('.csv')][0]; rows=[]
for ln in z.read(nm).decode('latin1').splitlines():
    p=[x.strip() for x in ln.split(',')]
    if len(p)>=5 and p[0].isdigit() and len(p[0])==8:
        d=pd.Timestamp(p[0])
        if d>END: continue
        rows.append((d,float(p[1])/100+float(p[4])/100,float(p[4])/100))
kf=pd.DataFrame(rows,columns=['d','mkt','rf']).set_index('d'); del rows
def ld(k):
    s=pd.read_csv(CL+k+'.csv',parse_dates=['date']).set_index('date')['r'].astype(float); return s[s.index<=END]
S={k:ld(k) for k in ['STAP','HLTH','UTIL']}
i3=S['STAP'].index.intersection(S['HLTH'].index).intersection(S['UTIL'].index)
d3=(S['STAP'].reindex(i3)+S['HLTH'].reindex(i3)+S['UTIL'].reindex(i3))/3
for a,b in (('1928-01-01','1985-12-31'),('1986-01-01','2014-12-31')):
    sl=lambda s: s[(s.index>=a)&(s.index<=b)]
    dm=sl(kf['mkt']-kf['rf']); dd=sl(d3).reindex(dm.index)-sl(kf['rf'])
    mo=lambda s: (1+s).groupby([s.index.year,s.index.month]).prod()-1
    mm=mo(sl(kf['mkt']))-mo(sl(kf['rf'])); md=mo(sl(d3))-mo(sl(kf['rf']))
    print(a[:4],b[:4],'daily sd ratio MKT/DEF3 %.3f  monthly sd ratio MKT/DEF3 %.3f  daily corr %.3f monthly corr %.3f'%(dm.std()/dd.std(),mm.std()/md.std(),dm.corr(dd),mm.corr(md)))
