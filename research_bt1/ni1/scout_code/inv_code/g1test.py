import sys,json,datetime as dt,numpy as np,pandas as pd
sys.path.insert(0,'/mnt/project-files/research/breakthrough/code'); import gate
o=pd.DataFrame(json.load(open(sys.argv[1])))
def known(r):
    y,m=r['y'],r['m']+2
    if m>12: y,m=y+1,m-12
    d18=pd.Timestamp(dt.date(y,m,18))
    if r['rel']:
        h=pd.Timestamp(r['rel'])
        if abs((h-d18).days)<=15: return h
    return d18
o['known']=o.apply(known,axis=1); o=o.sort_values(['y','m']).reset_index(drop=True)
lag=(o['known']-pd.to_datetime(dict(year=o.y,month=o.m,day=1))).dt.days
print('lag days from month start: min',lag.min(),'max',lag.max())
r=o['ratio']
feats={'d1':r.diff(1),'d3':r.diff(3),'d12':r.diff(12),
       'lvl_vs_expmed':r-r.expanding(24).median().shift(0)}
L=gate.labels()['ndx_86_14']; idx=L.index
res={}
for k,f in feats.items():
    s=pd.Series(f.values,index=o['known']+pd.Timedelta(days=1)).dropna()   # usable from the next day close
    s=s[~s.index.duplicated(keep="last")].sort_index()
    for inv in (False,True):
        sig=(s<=0) if not inv else (s>0)
        assert sig.index.is_monotonic_increasing, sig.index[:5]
        sig.index=pd.DatetimeIndex(sig.index).as_unit('us')
        g=gate.test(sig.astype(float),trials=8,name=f'{k}{"_inv" if inv else ""}',verbose=False)
        e=g['ndx_86_14']; res[f'{k}{"_inv" if inv else ""}']=(round(e['hit'],3),e['n'],round(e['always_up'],3),round(e['hit_deflated'],3),g['verdict'])
for k,v in res.items(): print(k,v)
# IC-style: correlation of feature with forward 21d NDX log return (block starts), 1996-2014
nd=gate.jp  # noqa
