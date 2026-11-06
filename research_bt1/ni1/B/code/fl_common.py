# NI1-B shared loaders: panel (adj, member only), OAP announcement indicator, time-valid link.
import lzma, io, numpy as np, pandas as pd
PANEL = '/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz'
LINK = '/mnt/project-files/research/influence/results/link_permno_col.csv'

def load_panel():
    z = np.load(io.BytesIO(lzma.open(PANEL).read()), allow_pickle=False)
    dates = z['dates'].astype('datetime64[D]'); adj = z['adj'].astype(np.float64)
    T = len(dates); mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)   # tickers/dvol/stale/divy not read
    return dates, adj, mem

def month_index(dates):
    ym = dates.astype('datetime64[M]').astype(int)       # months since 1970-01
    last = np.r_[ym[1:] != ym[:-1], True]
    me = np.where(last)[0]                                  # trading-day index of each month-end
    return ym, me, ym[me]

def ym_to_m(yyyymm):
    yyyymm = np.asarray(yyyymm); return (yyyymm // 100 - 1970) * 12 + (yyyymm % 100 - 1)

def announcement_matrix(oap, months):
    """I[k, permno] raw-OAP announcement indicator and R[k, permno] row-present, k over `months` (months since 1970-01)."""
    o = oap.sort_values(['permno', 'yyyymm']).reset_index(drop=True)
    o['m'] = ym_to_m(o.yyyymm.values)
    perm = np.unique(o.permno.values); pidx = {p: i for i, p in enumerate(perm)}
    m0 = months[0]; K = len(months)
    I = np.zeros((K, len(perm)), bool); R = np.zeros((K, len(perm)), bool)
    p = o.permno.values; m = o.m.values; a = o.AnnouncementReturn.values
    start = np.r_[0, np.where(p[1:] != p[:-1])[0] + 1, len(p)]
    for s, e in zip(start[:-1], start[1:]):
        j = pidx[p[s]]; last = np.nan; seen_row = False
        for i in range(s, e):
            k = m[i] - m0
            v = a[i]
            if np.isfinite(v):
                if np.isfinite(last):
                    ann = v != last
                else:
                    ann = seen_row
                if ann and 0 <= k < K: I[k, j] = True
                last = v
            if 0 <= k < K: R[k, j] = True
            seen_row = True
    return I, R, pidx

def link_by_month(mem_me, R, pidx):
    """L[k, col] = permno column index into I/R (or -1) valid at month-end k."""
    lk = pd.read_csv(LINK)
    K, N = mem_me.shape
    L = np.full((K, N), -1, int)
    for col, g in lk.groupby('col'):
        js = [pidx[p] for p in g.permno if p in pidx]
        if not js: continue
        pres = np.stack([R[:, j] for j in js], 1)
        one = pres.sum(1) == 1
        choice = np.array(js)[pres.argmax(1)]
        L[one, col] = choice[one]
    L[~mem_me] = -1
    # one permno on two member columns in the same month -> drop both
    for k in range(K):
        v = L[k][L[k] >= 0]
        if len(v) != len(np.unique(v)):
            u, c = np.unique(v, return_counts=True); bad = u[c > 1]
            L[k][np.isin(L[k], bad)] = -1
    return L
