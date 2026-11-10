import lzma, io, os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'code'))
import paths
P = paths.PROJ + '/research/data/'
_z={}
def _load(fn):
    if fn not in _z:
        with lzma.open(P+fn) as f: _z[fn]=np.load(io.BytesIO(f.read()), allow_pickle=False)
    return _z[fn]
def sym(k, fn='panel_f32.npz.xz'):
    z=_load(fn); ts=z[k+'|ts']; v=z[k+'|v'].astype('float64')
    idx=pd.to_datetime(ts, unit='s', utc=True)
    tz='Asia/Seoul' if k.endswith('.KS') else 'America/New_York'
    d=idx.tz_convert(tz).normalize().tz_localize(None)
    df=pd.DataFrame(v, index=d, columns=['open','high','low','close','adj','vol'])
    df=df[~df.index.duplicated(keep='last')]
    return df
if __name__=='__main__':
    pd.set_option('display.width',200)
    for k in ['QQQ','_NDX','_IRX','SPY','TQQQ','069500.KS','122630.KS','114800.KS','KRW_X','TLT','IEF','_GSPC']:
        d=sym(k); print(k, d.index[0].date(), d.index[-1].date(), len(d), 'nan close', d.close.isna().sum(), 'nan open', d.open.isna().sum())
    d=sym('_TNX','panel_ext_f32.npz.xz'); print('_TNX', d.index[0].date(), d.index[-1].date(), len(d), d.close.isna().sum())
    q=sym('QQQ'); print(q.head(8)); print(q.tail(4))
    print('open==prevclose', (q.open==q.close.shift()).sum(), 'open==high', (q.open==q.high).mean(), 'open==low', (q.open==q.low).mean())
    for a,b in [('1999','2000'),('2001','2004'),('2005','2012'),('2013','2026')]:
        s=q.loc[a:b]; print(a,b,'open==high %.3f open==low %.3f open outside HL %.4f'%((s.open==s.high).mean(),(s.open==s.low).mean(),((s.open>s.high+1e-6)|(s.open<s.low-1e-6)).mean()))
    for k in ['069500.KS','122630.KS','114800.KS']:
        d=sym(k); print(k); print(d.head(3)); print(d.tail(2)); print('zero vol days', (d.vol==0).sum(), 'open nan/0', ((d.open.isna())|(d.open==0)).sum())
