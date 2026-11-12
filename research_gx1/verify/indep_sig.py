"""Independent rebuild of GX1 world signals (historical + path) on a given calendar; compare to gx1lib."""
import sys, time; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, pandas as pd, numpy as np
EUROJ = {**{m: pd.Timestamp('1999-01-01') for m in ('DE','FR','IT','ES','NL','BE','AT','IE','PT')}, 'GR': pd.Timestamp('2001-01-01')}
def region(m): return G.REGION[m]
def lvl_age(cal, m):
    s = G.index(m).rename('close').reset_index().rename(columns={'date':'d'}); s['d2']=s['d']
    q = pd.DataFrame({'t': cal})
    r = pd.merge_asof(q, s, left_on='t', right_on='d', direction='backward', allow_exact_matches=False)
    age = (r['t'] - r['d2']).dt.days.values.astype(float)
    L = np.where(age <= 31, r['close'].values, np.nan)
    age = np.where(age <= 31, age, np.inf)
    return L, age
def mrate(cal, sid):
    f = G._rate_file(sid); x = pd.read_csv(f, parse_dates=['observation_date']).iloc[:, :2]; x.columns=['obs','v']
    x['v']=pd.to_numeric(x['v'],errors='coerce'); x=x.dropna()
    x['avail'] = x['obs'] + pd.offsets.MonthBegin(1)   # obs dated 1st of month m -> usable from 1st of m+1
    q = pd.DataFrame({'t': cal}); r = pd.merge_asof(q, x.sort_values('avail'), left_on='t', right_on='avail', direction='backward')
    ageM = (r['t'].dt.year*12 + r['t'].dt.month) - (r['obs'].dt.year*12 + r['obs'].dt.month)
    return np.where(ageM <= 3, r['v'].values, np.nan)
def runlen(v):
    out = np.zeros(len(v), int); c = 0
    for i, b in enumerate(v): c = c + 1 if b else 0; out[i] = c
    return out
def ind_one(L, valid):
    T=len(L); rl=runlen(valid); s=pd.Series(np.where(valid,L,np.nan))
    m200=s.rolling(200).mean().values; mx=s.rolling(252).max().values; lag=s.shift(126).values
    with np.errstate(invalid='ignore'):
        return {'B200': (np.where(rl>=200, L<m200, False), rl>=200), 'D20': (np.where(rl>=252, L/mx-1 <= -0.2, False), rl>=252),
                'N126': (np.where(rl>=127, L/lag-1 < 0, False), rl>=127)}
def inv_raw(cal, mk, AGE):
    out={}
    for j,m in enumerate(mk):
        if m not in G.OECD: continue
        cc=G.OECD[m]; s3='IR3TCD01JPM156N' if m=='JP' else 'IR3TIB01%sM156N'%cc; sl='IRLTLT01%sM156N'%cc
        if G._rate_file(s3) is None or G._rate_file(sl) is None: continue
        y3=mrate(cal,s3); y10=mrate(cal,sl); v=(~np.isnan(y3))&(~np.isnan(y10))&(AGE[:,j]<=10)
        with np.errstate(invalid='ignore'): out[m]=(v&((y10-y3)<0), v)
    return out
def inv_share_seq(raw, dates, rows):
    """rows: 1-D source-row sequence (history: arange). returns num, den"""
    T=len(rows); num=np.zeros(T); den=np.zeros(T); ean=np.zeros(T); ead=np.zeros(T); d=dates[rows]
    for m,(ir,v) in raw.items():
        a=ir[rows]; vv=v[rows]
        fl=pd.Series(a.astype(float)).rolling(378,min_periods=1).max().values>0
        fl=fl&vv
        if m in EUROJ:
            ina = d>=EUROJ[m]
            num+=np.where(ina,0,fl); den+=np.where(ina,0,vv); ean+=np.where(ina,fl,0); ead+=np.where(ina,vv,0)
        else: num+=fl; den+=vv
    ev=ead>=1; et=ev&(ean>ead/2)
    return num+et, den+ev
def hist_signals(cal, host):
    mk=[m for m in G.MARKETS if region(m)!=region(host)]; T=len(cal)
    LA=[lvl_age(cal,m) for m in mk]; L=np.column_stack([a[0] for a in LA]); AGE=np.column_stack([a[1] for a in LA])
    num={k:np.zeros(T) for k in ('B200','D20','N126')}; den={k:np.zeros(T) for k in num}
    for j in range(len(mk)):
        ind=ind_one(L[:,j], ~np.isnan(L[:,j])); fr=AGE[:,j]<=10
        for k in num: f,v=ind[k]; v=v&fr; num[k]+=f&v; den[k]+=v
    raw=inv_raw(cal,mk,AGE); num['INV'],den['INV']=inv_share_seq(raw, cal, np.arange(T))
    on=cal>=pd.Timestamp('1989-01-01'); out={}
    for i,(k,th) in enumerate(G.SIGNALS):
        sh=np.where((den[k]>=5)&on, num[k]/np.maximum(den[k],1), -1); out['G%02d'%i]=sh>=th
    return out, dict(L=L,AGE=AGE,mk=mk,raw=raw,num=num,den=den)
def path_signals(cal, ii, host, aux, paths):
    L=aux['L']; AGE=aux['AGE']; mk=aux['mk']; raw=aux['raw']; out={('G%02d'%i):np.zeros((len(paths),ii.shape[1]),bool) for i in range(13)}
    on_src=cal>=pd.Timestamp('1989-01-01')
    for pi,p in enumerate(paths):
        pos=ii[p]; T=len(pos); num={k:np.zeros(T) for k in ('B200','D20','N126')}; den={k:np.zeros(T) for k in num}
        for j in range(len(mk)):
            a=L[pos,j]; b=L[pos-1,j]; ok=~np.isnan(a)&~np.isnan(b); ok[0]=False
            r=np.where(ok, a/np.where(ok,b,1)-1, 0.0); lv=np.cumprod(1+r)
            ind=ind_one(lv, ok); fr=AGE[pos,j]<=10
            for k in num: f,v=ind[k]; v=v&fr; num[k]+=f&v; den[k]+=v
        num['INV'],den['INV']=inv_share_seq(raw, cal, pos)
        on=on_src[pos]
        for i,(k,th) in enumerate(G.SIGNALS):
            sh=np.where((den[k]>=5)&on, num[k]/np.maximum(den[k],1), -1); out['G%02d'%i][pi]=sh>=th
    return out
if __name__=='__main__':
    which=sys.argv[1]
    if which=='us':
        fr=G.us_frames()
        for bn in ('real_ndx_86_14','dev250_glued','real_spx_70_85'):
            X,F,ii,kind=fr[bn]; cal=X.index; t=time.time()
            mine,aux=hist_signals(cal,'US'); D=G.world_signals(cal,'US')
            mm={c:int((mine[c]!=D[c].values).sum()) for c in mine}; sc=ii[0] if bn!='dev250_glued' else np.unique(ii)
            mms={c:int((mine[c][sc]!=D[c].values[sc]).sum()) for c in mine}
            print(bn,'T',len(cal),'mismatch all rows',mm,'| on used rows',mms, 'on-share G11 used rows %.4f'%mine['G11'][sc].mean(), '%.0fs'%(time.time()-t), flush=True)
            if bn=='dev250_glued':
                paths=list(range(0,500,25)); mp=path_signals(cal,ii,'US',aux,paths); gp=G.path_world(cal,ii,'US')
                print('path mismatch (20 paths):',{c:int((mp[c]!=gp[c][paths]).sum()) for c in mp}, 'cells', 20*ii.shape[1])
                print('path G11 on-share used rows (all 500, gx1): %.4f ; mine 20 paths %.4f vs gx1 same 20 %.4f'%(gp['G11'][:,G.W:].mean(), mp['G11'][:,G.W:].mean(), gp['G11'][paths][:,G.W:].mean()))
    else:
        for h in sys.argv[2:]:
            X,i0=G.host(h); cal=X.index; mine,aux=hist_signals(cal,h); D=G.world_signals(cal,h)
            print(h,{c:int((mine[c]!=D[c].values).sum()) for c in mine}, flush=True)
