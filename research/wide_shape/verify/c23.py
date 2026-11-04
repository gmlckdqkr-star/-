import numpy as np, pandas as pd
W='/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/'
K=np.load(W+'kr_arrays.npz',allow_pickle=True); D=np.load(W+'kr_derived.npz',allow_pickle=True)
dates=K['dates']; hs=D['hs']; trade=D['trade']; listed=D['listed']; amt=np.nan_to_num(K['amount'])
print('hs finite frac among trade',np.isfinite(hs[trade]).mean(), 'hs quantiles',np.nanpercentile(hs[trade],[5,25,50,75,95]))
m=(dates>=np.datetime64('1999-01-01'))
a20=pd.DataFrame(amt).rolling(20).sum().values/20
age=np.cumsum(listed,0)
el=trade&(a20>=1e8)&(age>=20)&m[:,None]&np.isfinite(hs)
c=2*hs[el]+0.003+2*0.00015
print('n obs',el.sum(),'median %.3f%% mean %.3f%% p10 %.3f p90 %.3f'%(np.median(c)*100,c.mean()*100,*np.percentile(c,[10,90])*100))
# by year median
yr=dates.astype('datetime64[Y]').astype(int)+1970
for y in (1999,2004,2009,2014):
    mm=el&(yr==y)[:,None]; cc=2*hs[mm]+0.0033; print(y,'median %.3f%%'%(np.median(cc)*100))
# check 3
st=pd.read_csv('/mnt/project-files/research/data/kr_stocks/staging_clean_a/KR_STOCKS.csv',dtype=str)
excl=set(st.loc[st['exclude'].notna(),'code']); st=st[~st.code.isin(excl)&(st.code.str[-1]=='0')]
st=st.sort_values(['code','start']).groupby('code').last()
OK=('피흡수합병','증권거래소 상장','유가증권시장 상장','코스닥시장 상장','신청에 의한 상장폐지','지주회사','합병','이전상장')
dl=st[st.status_2014=='delisted'].copy(); dl['r']=dl.end_reason.fillna('')
dl['fail']=[not any(k in r for k in OK) for r in dl.r]
print(dl.fail.value_counts().to_dict(), 'reason counts fail:'); print(dl[dl.fail].r.value_counts().head(8).to_string())
codes=list(K['codes']); close=K['close']
rng=np.random.RandomState(0)
for flag in (True,False):
    sub=dl[dl.fail==flag]; pick=sub.index[rng.permutation(len(sub))[:10]]
    print('=== fail=',flag)
    for cd in pick:
        j=codes.index(cd); ok=np.where(np.isfinite(close[:,j]))[0]
        if len(ok)==0: print(cd,'no price'); continue
        s=close[ok[-60:],j]
        print(cd,st.loc[cd,'name_marcap_last_le2014'],'| end',st.loc[cd,'end'],'| reason:',dl.loc[cd,'r'],'| 60d start %.0f min %.0f last %.0f (last/start %.2f) lastdate %s'%(s[0],s.min(),s[-1],s[-1]/s[0],str(dates[ok[-1]])))
