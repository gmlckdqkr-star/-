"""M3 (a) bond risk-premium gates (PRECOMMIT_M3.md sec 1). Every gate value at date d uses data through close d only.
Sources (cut at 2014-12-31 on download): GSW zero curve (Fed feds200628), ACM term premium (NY Fed, full-sample estimate ->
NOT point-in-time, upper-bound sensitivity only), H.15 CMT 1y/10y (project raw file).
gates() -> DataFrame (by date, float 1.0 on / 0.0 off / NaN undefined) with columns CP0 CPmed FB0 FBmed SLmed ACM0 ACMmed."""
import os, numpy as np, pandas as pd
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/'
END = pd.Timestamp('2014-12-31')
REAL = ['CP0', 'CPmed', 'FB0', 'FBmed', 'SLmed']
ACM = ['ACM0', 'ACMmed']
ALL = REAL + ACM
MINPAIRS = 120          # >= 10 years of realized monthly (x_s, rx_{s+12}) pairs before the first CP estimate
MINDAYS = 2520          # >= 10 years of daily history before an expanding median is defined


def gsw():
    d = pd.read_csv(SCR + 'data/gsw_le2014.csv', index_col=0, parse_dates=True)
    d = d[d.index <= END]
    y = d[['SVENY%02d' % n for n in range(1, 6)]].dropna() / 100.0
    y.columns = [1, 2, 3, 4, 5]
    return y


def fwd(y):
    """log forward rates f1 = y1, fn = n*yn - (n-1)*y(n-1)"""
    f = pd.DataFrame(index=y.index)
    f[1] = y[1]
    for n in range(2, 6): f[n] = n * y[n] - (n - 1) * y[n - 1]
    return f


def cp_daily(y):
    """expanding-window CP: returns (cp_daily Series, cpmed_threshold Series, estimates list)"""
    f = fwd(y); X = f[[1, 2, 3, 4, 5]]
    me = y.groupby([y.index.year, y.index.month]).tail(1)          # last available day of each month
    Xm = X.loc[me.index].values; ym = me.values                      # (M,5)
    M = len(me)
    rx = np.full(M, np.nan)
    for j in range(M - 12):
        a, b = ym[j], ym[j + 12]
        r = [n * a[n - 1] - (n - 1) * b[n - 2] - a[0] for n in range(2, 6)]   # rx(n) = p(n-1)_{t+12} - p(n)_t - y1_t
        rx[j] = np.mean(r)
    cp = pd.Series(np.nan, index=X.index); thr = pd.Series(np.nan, index=X.index); est = []
    Xd = np.c_[np.ones(len(X)), X.values]
    for i in range(M):
        npair = i - 12 + 1                                           # pairs j = 0..i-12 realized by month-end i
        if npair < MINPAIRS: continue
        A = np.c_[np.ones(npair), Xm[:npair]]; g, *_ = np.linalg.lstsq(A, rx[:npair], rcond=None)
        med = float(np.median(A @ g))
        d0 = me.index[i]; d1 = me.index[i + 1] if i + 1 < M else END + pd.Timedelta(days=1)
        m = (X.index > d0) & (X.index <= d1)                          # applied from the next trading day through next month-end
        cp[m] = Xd[m] @ g; thr[m] = med
        est.append(dict(T=str(d0.date()), npair=npair, g=g.tolist(), fit_med=med, r2=float(1 - np.var(rx[:npair] - A @ g) / np.var(rx[:npair]))))
    return cp, thr, est


def expmed_gate(s):
    s = s.dropna(); med = s.expanding().median(); cnt = np.arange(1, len(s) + 1)
    g = (s > med).astype(float); g[cnt < MINDAYS] = np.nan
    return g


def h15():
    df = pd.read_csv('/mnt/project-files/research/broad_etf/data/raw/h15/H15_all_daily.csv', skiprows=5, index_col=0, na_values=['ND', ''])
    df.index = pd.to_datetime(df.index); df = df[df.index <= END]
    df.columns = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
    return df.astype(float) / 100.0


def acm():
    d = pd.read_csv(SCR + 'data/acm_ACM_Daily_le2014.csv', parse_dates=['DATE']).set_index('DATE')
    d = d[d.index <= END]
    return d['ACMTP10'].astype(float).dropna() / 100.0


_G = {}
def gates():
    if 'g' in _G: return _G['g']
    fn = SCR + 'cache/m3_gates.pkl'
    if os.path.exists(fn): _G['g'] = pd.read_pickle(fn); return _G['g']
    y = gsw(); f = fwd(y)
    cp, thr, est = cp_daily(y)
    out = {}
    out['CP0'] = (cp > 0).astype(float).where(cp.notna())
    out['CPmed'] = (cp > thr).astype(float).where(cp.notna())
    fb = f[5] - f[1]
    out['FB0'] = (fb > 0).astype(float)
    out['FBmed'] = expmed_gate(fb)
    h = h15(); sl = (h['y10'] - h['y1']).dropna()
    out['SLmed'] = expmed_gate(sl)
    tp = acm()
    out['ACM0'] = (tp > 0).astype(float)
    out['ACMmed'] = expmed_gate(tp)
    G = pd.DataFrame(out).sort_index(); G = G[G.index <= END]
    G.attrs = {}
    pd.to_pickle(G, fn)
    pd.DataFrame(est).to_csv(SCR + 'results/cp_estimates.csv', index=False)
    pd.DataFrame({'cp': cp, 'thr': thr, 'fb': fb}).to_pickle(SCR + 'cache/m3_cp_raw.pkl')
    _G['g'] = G; return G


def on_basis(dates, name):
    """gate on a basis calendar: last value at or before each date (ffill), undefined -> 0 (off = cash)"""
    s = gates()[name].dropna()
    v = s.reindex(s.index.union(dates)).ffill().reindex(dates)
    return np.nan_to_num(v.values.astype(float), nan=0.0)


if __name__ == '__main__':
    G = gates()
    for c in G.columns:
        s = G[c].dropna(); print(c, 'first', s.index[0].date(), 'n', len(s), 'on-share %.2f' % s.mean())
