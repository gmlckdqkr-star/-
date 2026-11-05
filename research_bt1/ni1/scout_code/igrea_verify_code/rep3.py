import sys, numpy as np, pandas as pd, openpyxl
from scipy.stats import spearmanr, rankdata
S='/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/ni1/scout/igrea_verify'
ig=pd.read_csv(S+'/igrea.csv',header=None,names=['m','v']); ig.index=pd.PeriodIndex(ig.m,freq='M'); ig=ig.v
def block(start,end):
    L=open(S+'/kf/17_Industry_Portfolios.csv').read().splitlines()
    hdr=[h.strip() for h in L[start].split(',')]; rows=[]
    for l in L[start+1:end]:
        p=l.split(',')
        if len(p)<5 or not p[0].strip().isdigit(): continue
        rows.append([p[0].strip()]+[float(x) for x in p[1:]])
    df=pd.DataFrame(rows,columns=['d']+hdr[1:]); df.index=pd.PeriodIndex(pd.to_datetime(df.d,format='%Y%m'),freq='M'); return df.drop(columns='d')
L=open(S+'/kf/17_Industry_Portfolios.csv').read().splitlines()
iv=[i for i,l in enumerate(L) if 'Average Value Weighted Returns -- Monthly' in l][0]
ie=[i for i,l in enumerate(L) if 'Average Equal Weighted Returns -- Monthly' in l][0]
ia=[i for i,l in enumerate(L) if 'Average Value Weighted Returns -- Annual' in l][0]
VW=block(iv+1,ie); EW=block(ie+1,ia)
wb=openpyxl.load_workbook('/mnt/project-files/research/open_data/raw/CMO_monthly.xlsx',read_only=True,data_only=True)
rows=list(wb['Monthly Prices'].iter_rows(min_row=7,values_only=True))
cm=pd.DataFrame([(r[0],r[1],r[64]) for r in rows if r[0] and 'M' in str(r[0])],columns=['m','oil','cu'])
cm.index=pd.PeriodIndex([pd.Period(year=int(s[:4]),month=int(s[5:]),freq='M') for s in cm.m]); cm=cm[['oil','cu']].apply(pd.to_numeric,errors='coerce')
CYC=['Mines','Steel','Machn','Chems','Trans']; DEF=['Food','Utils','Cnsum']
def run(R,lab,lag=1,k=3,h=1):
    spread=R[CYC].mean(1)-R[DEF].mean(1); mkt=R.mean(1)
    d=pd.DataFrame({'sp':spread,'mkt':mkt})
    d['sig']=(ig-ig.shift(k)).shift(lag)     # known at end of month t-1 -> predicts month t
    d['cu']=np.log(cm.cu).diff(k).shift(lag); d['oil']=np.log(cm.oil).diff(k).shift(lag)
    d['psp']=spread.rolling(3).sum().shift(1); d['pm']=mkt.rolling(3).sum().shift(1)
    d['y']=spread.rolling(h).sum().shift(-(h-1))
    d=d.loc['1969-01':'2014-12'].dropna()
    def pc(x,y,Z):
        rx=rankdata(x); ry=rankdata(y); Zr=np.column_stack([np.ones(len(x))]+[rankdata(z) for z in Z])
        ex=rx-Zr@np.linalg.lstsq(Zr,rx,rcond=None)[0]; ey=ry-Zr@np.linalg.lstsq(Zr,ry,rcond=None)[0]
        return np.corrcoef(ex,ey)[0,1]
    out=[]
    for a,b in [('1969','1985'),('1986','1999'),('2000','2014'),('1986','2014'),('1969','2014')]:
        s=d.loc[a:b]; n=len(s)
        r=spearmanr(s.sig,s.y)[0]; p1=pc(s.sig.values,s.y.values,[s.psp.values,s.pm.values]); p2=pc(s.sig.values,s.y.values,[s.psp.values,s.pm.values,s.cu.values,s.oil.values])
        rm=spearmanr(s.sig,s.mkt)[0] if h==1 else np.nan
        out.append(f'{a}-{b} n={n} rho={r:+.3f} t~{r*np.sqrt(n/h):.1f} | partial(psp,mkt)={p1:+.3f} | +cu,oil={p2:+.3f} | mkt rho={rm:+.3f}')
    print(f'== {lab} lag={lag} k={k} h={h}'); print('\n'.join(out))
    return d

import warnings; warnings.filterwarnings('ignore')
ff=[l.split(',') for l in open('/mnt/project-files/research/data/ken_french/raw/mirror_a91quaini/F-F_Research_Data_Factors.CSV').read().splitlines()]
ff=[r for r in ff if len(r)>=5 and r[0].strip().isdigit() and len(r[0].strip())==6]
rf=pd.Series([float(r[4]) for r in ff],index=pd.PeriodIndex(pd.to_datetime([r[0].strip() for r in ff],format='%Y%m'),freq='M'))
R=VW; cyc=R[CYC].mean(axis=1); de=R[DEF].mean(axis=1); allm=R.mean(axis=1)
x=pd.DataFrame({'sig':(ig-ig.shift(3)).shift(2),'c':cyc,'d':de,'m':allm,'rf':rf}).loc['1969':'2014'].dropna()
med=x.sig.expanding(60).median().shift(1); on=(x.sig>med)
x['lo']=np.where(on,x.c,x.d); x['mix']=(x.c+x.d)/2
x=x[med.notna()]
for a,b in [('1974','1985'),('1986','1999'),('2000','2014'),('1986','2014')]:
    q=x.loc[a:b]
    def sh(z): e=(z-q.rf)/100; return e.mean()/e.std()*np.sqrt(12), ((1+z/100).prod()**(12/len(z))-1)*100
    print(a,b,'longonly switch SR %.2f CAGR %.1f | 50/50 mix SR %.2f CAGR %.1f | mkt17 SR %.2f CAGR %.1f'%(*sh(q.lo),*sh(q.mix),*sh(q.m)))
    print('   frac months in CYC %.2f, switches/yr %.1f'%(on.loc[q.index].mean(), (on.loc[q.index].astype(int).diff().abs().sum())/len(q)*12))
