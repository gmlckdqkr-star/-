"""verify7/proxy: sensitivity checks of the trend proxy (USD off-calendar days, execution lag, rebalance phase). <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
sys.path.insert(0, '/mnt/project-files/research/df1/verify7/proxy')
import df7 as D, df5data as DD, df5lib as L
OUT = '/tmp/df7v_proxy/proxy_sens.json'
X, S = L._src('1984-01-03', '2014-12-31', 'SPX'); idx = S.index; rf = S['M_rf'].fillna(0.0); src = DD.src_series()
MK = ['SPX', 'LTT', 'GOLD', 'USD', 'DEVX']

def build_ex(usd_fix=False):
    ex = pd.DataFrame(index=idx); ex['SPX'] = S['SPX'] - rf
    for k in ('LTT', 'GOLD', 'USD', 'DEVX'):
        s0 = src[k]
        if usd_fix and k == 'USD':     # compound off-calendar days into the next calendar day
            s0 = s0[s0.index >= idx.min()]
            pos = idx.searchsorted(s0.index)                      # next calendar day (or same)
            pos = np.minimum(pos, len(idx) - 1)
            s0 = np.log1p(s0).groupby(idx[pos]).sum().pipe(np.expm1)
        s = s0.reindex(idx); first = s0.index.min(); s[s.index >= first] = s[s.index >= first].fillna(0.0); ex[k] = s - rf
    return ex

def trend(ex, V=0.12, lbs=(63, 126, 252), volw=60, reb=5, cap=3.0, lag=1, phase=0):
    lg = np.log1p(ex); cum = lg.cumsum()
    sig = sum(np.sign(cum - cum.shift(L_)) for L_ in lbs) / len(lbs)
    vol = ex.rolling(volw).std() * np.sqrt(252)
    ok = cum.shift(max(lbs)).notna() & vol.notna(); N = ok.sum(axis=1).replace(0, np.nan)
    w = (sig / vol).mul(V / np.sqrt(N), axis=0).clip(-cap, cap).where(ok, 0.0).shift(lag)
    keep = (np.arange(len(ex)) - phase) % reb == 0
    w = w.where(pd.Series(keep, index=ex.index), np.nan).ffill().fillna(0.0)
    return w, (w * ex.fillna(0.0)).sum(axis=1)

def st(x, f=252):
    return dict(mean_ann=float(x.mean() * f), vol_ann=float(x.std() * np.sqrt(f)), sharpe=float(x.mean() / x.std() * np.sqrt(f)))
def per(t):
    return {p: st(t[(t.index >= a) & (t.index <= b)]) for p, (a, b) in
            {'1986_2014': ('1986-01-01', '2014-12-31'), '1986_1999': ('1986-01-01', '1999-12-31'), '2000_2014': ('2000-01-01', '2014-12-31')}.items()}
R = {}
ex = build_ex(); w, tr = trend(ex); assert (tr - D.trend_by_date()['tr']).abs().max() == 0
R['base'] = per(tr)
u = src['USD']; u = u[u.index >= idx.min()]; off = u[~u.index.isin(idx)]
R['usd_off_cal'] = dict(n=int(len(off)), sum_ret=float(off.sum()), abs_sum=float(off.abs().sum()), first=str(off.index.min().date()), last=str(off.index.max().date()),
                       weekday_counts={str(k): int(v) for k, v in off.index.dayofweek.value_counts().sort_index().items()},
                       years={str(k): int(v) for k, v in off.index.year.value_counts().sort_index().items()})
nanc = src['USD'].reindex(idx); R['usd_nan_on_cal'] = [str(x.date()) for x in nanc[(nanc.index >= src['USD'].index.min()) & nanc.isna()].index]
exf = build_ex(usd_fix=True); wf, trf = trend(exf); R['usd_fix'] = per(trf)
R['usd_cum_excess_base_vs_fix'] = dict(base=float(np.expm1(np.log1p(ex['USD'][ex.index >= '1986-01-01']).sum())), fix=float(np.expm1(np.log1p(exf['USD'][exf.index >= '1986-01-01']).sum())))
R['lag2'] = per(trend(ex, lag=2)[1])
R['phase'] = {str(ph): per(trend(ex, phase=ph)[1])['1986_2014'] for ph in range(5)}
R['daily_reb'] = per(trend(ex, reb=1)[1])
json.dump(R, open(OUT, 'w'), indent=1)
print(json.dumps(R, indent=1))
