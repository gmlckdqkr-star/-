"""VXR1 data: CM1 (30-day constant-maturity VIX futures) daily returns from Cboe CFE VX settles, <=2014 only (PRECOMMIT_VXR1.md s1)."""
import pandas as pd, numpy as np, glob, re, os
END = pd.Timestamp('2014-12-31')
DD = '/mnt/project-files/research/vxr1/data/'
MM = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

def parse_raw(rawdir):
    """raw Cboe files -> long table (date, ym, px), cut at 2014-12-31 BEFORE anything else"""
    rows = []
    for f in sorted(glob.glob(rawdir + '/*.csv')):
        if 'VIX_History' in f: continue
        L = [l.rstrip('\r\n').split(',') for l in open(f) if l.strip()]
        i = [k for k, l in enumerate(L) if l[0].strip() == 'Trade Date'][0]
        d = pd.DataFrame([l[:11] for l in L[i + 1:] if len(l) >= 11], columns=[c.strip() for c in L[i][:11]])
        d['date'] = pd.to_datetime(d['Trade Date'])
        for c in ['Close', 'Settle']: d[c] = pd.to_numeric(d[c], errors='coerce')
        m = d['Futures'].str.extract(r'\((\w{3}) (\d{2,4})\)')
        y = m[1].astype(int); y = np.where(y < 100, y + 2000, y)
        d['ym'] = y * 100 + m[0].map(MM)
        rows.append(d[['date', 'ym', 'Close', 'Settle']])
    A = pd.concat(rows).drop_duplicates(['date', 'ym'])
    exp = A.groupby('ym').date.max()                 # last trade date in file (needs full file: computed before cut)
    A = A[A.date <= END].copy()
    A['px'] = np.where(A.Settle > 0, A.Settle, np.where(A.Close > 0, A.Close, np.nan))
    A['exp'] = A.ym.map(exp)
    A['px'] = np.where(A.date < pd.Timestamp('2007-03-26'), A.px / 10.0, A.px)   # old 10x quotation (VBI) -> VIX points
    return A.dropna(subset=['px'])[['date', 'ym', 'exp', 'px']]

def cm1(A):
    """daily CM1 return series (index = date), plus M1 level (/10 before 2007-03-26) and weights"""
    P = A.pivot(index='date', columns='ym', values='px').sort_index()
    E = A.groupby('ym').exp.first()
    dates = P.index; out = []
    prev = None
    for t in dates:
        if prev is not None:
            w = prev['w']; num = 0.0; den = 0.0
            for ym, wi in w.items():
                a, b = P.at[prev['t'], ym], P.at[t, ym] if t in P.index else np.nan
                if np.isfinite(a) and np.isfinite(b) and a > 0: num += wi * (b / a - 1); den += wi
            r = num / den if den > 0.5 else np.nan
        else: r = np.nan
        # weights for next day: M1 = nearest contract expiring AFTER t, M2 = next
        live = [ym for ym in E.index if E[ym] > t and np.isfinite(P.at[t, ym]) if ym in P.columns]
        live = sorted(live, key=lambda y: E[y])
        if len(live) >= 2:
            T1 = (E[live[0]] - t).days; T2 = (E[live[1]] - t).days
            w1 = min(1.0, max(0.0, (T2 - 30) / max(T2 - T1, 1)))
            lvl = (w1 * P.at[t, live[0]] + (1 - w1) * P.at[t, live[1]]) 
            prev = dict(t=t, w={live[0]: w1, live[1]: 1 - w1}); out.append((t, r, lvl, T1, T2, w1))
        else:
            out.append((t, r, np.nan, np.nan, np.nan, np.nan)); prev = None
    D = pd.DataFrame(out, columns=['date', 'r', 'lvl', 'T1', 'T2', 'w1']).set_index('date')
    return D

def build(rawdir='/tmp/claude-0/vx/raw'):
    A = parse_raw(rawdir); D = cm1(A)
    first = D['r'].first_valid_index(); D = D[D.index >= first]
    os.makedirs(DD, exist_ok=True)
    A.to_csv(DD + 'vx_settles_le2014.csv', index=False); D.to_csv(DD + 'cm1_le2014.csv')
    v = pd.read_csv(rawdir + '/VIX_History.csv', parse_dates=['DATE']).set_index('DATE')['CLOSE']
    v[v.index <= END].to_csv(DD + 'vix_le2014.csv')
    return D

def load():
    D = pd.read_csv(DD + 'cm1_le2014.csv', parse_dates=['date']).set_index('date')
    return D[D.index <= END]

if __name__ == '__main__':
    D = build(); print(D.head(3)); print(D.tail(3)); print('n', D['r'].notna().sum(), 'first', D.index[0])
