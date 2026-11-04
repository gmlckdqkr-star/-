"""research/etf_ext (thread '이전 성과 확장해 s0.85 넘기', 2026-11-04). <=2014 ONLY: every source is cut at 2014-12-31 first.
By-date daily simple returns of the wider ETF universe = BE1 bdata.by_date (KF sectors/styles, H.15 synthetic Treasuries, gold,
panel ETFs spliced after listing; verified in BE1) + user_port_up updata.by_date (SPX TR, GOLD, TB trend proxy, TS plain TSMOM, SOX)
+ new streams built here: EDV (25y zero, H.15), MTUM-p / QUAL-p (KF 6 ME x Prior12-2 / ME x OP, big high), EFA-p / VGK-p / EWJ-p
(KF regional market, 1990-07+ only = real-only). Leveraged / stacked products are built in etxeng from these streams."""
import sys, os, io, zipfile, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/broad_etf/code')
sys.path.insert(0, '/mnt/project-files/research/user_port_up/code')
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import bdata as BD
END = pd.Timestamp('2014-12-31')
RAW = '/mnt/project-files/research/etf_ext/data/raw/'
CACHE = '/tmp/claude-0/-home-user--/02b33b90-28e2-5e40-8793-82eef7278142/scratchpad/etx_cache/'
os.makedirs(CACHE, exist_ok=True)
BD.CACHE = CACHE  # keep BE1's by-date cache inside this session


def _kf(fn, section=0):
    z = zipfile.ZipFile(RAW + 'kf/' + fn); txt = z.read(z.namelist()[0]).decode('latin1').splitlines()
    blocks, cur = [], None
    for ln in txt:
        p = [x.strip() for x in ln.split(',')]
        if len(p) > 1 and p[0] == '' and cur is None: cur = {'cols': p[1:], 'rows': []}; continue
        if cur is not None:
            if len(p) > 1 and p[0].isdigit() and len(p[0]) == 8: cur['rows'].append(p)
            else: blocks.append(cur); cur = None
    if cur: blocks.append(cur)
    b = blocks[section]
    df = pd.DataFrame([r[1:] for r in b['rows']], index=pd.to_datetime([r[0] for r in b['rows']]), columns=b['cols']).astype(float)
    df = df[df.index <= END]                      # cut first
    return df.where(df > -99.0) / 100.0


def zero_ret(y, M, fee):
    """zero-coupon bond total return from a CMT yield (decimal), maturity M years (semiannual comp): carry + duration + convexity"""
    y = y.dropna(); dt = y.index.to_series().diff().dt.days.fillna(1).values / 365.0
    y0 = y.shift(1).values; dy = y.diff().values
    D = M / (1 + y0 / 2)                          # modified duration of a zero
    C = M * (M + 0.5) / (1 + y0 / 2) ** 2          # convexity of a zero (semiannual)
    r = y0 * dt - D * dy + 0.5 * C * dy ** 2 - fee * dt
    return pd.Series(r, index=y.index).iloc[1:]


def by_date():
    fn = CACHE + 'etx_bydate.pkl'
    if os.path.exists(fn): return pd.read_pickle(fn)
    D = BD.by_date(actual=True).copy()
    import updata as UD
    U = UD.by_date()
    for k in ['SPX', 'GOLD', 'TB', 'TS', 'SOX']: D['U_' + k] = U[k].reindex(D.index.union(U.index))
    D = D.reindex(D.index.union(U.index))
    for k in ['SPX', 'GOLD', 'TB', 'TS', 'SOX']: D['U_' + k] = U[k].reindex(D.index)
    h = BD._h15()
    z30 = zero_ret(h['y30'], 25, 0.0006); z20 = zero_ret(h['y20'], 20, 0.0006)
    edv = z30.combine_first(z20 * 1.0)             # 30y CMT where published, else 20y CMT (shorter zero, conservative)
    D['EDV'] = edv.reindex(D.index)
    fe = 0.012 / 252                               # BE1 equity proxy charge: 0.4 % fee + 0.8 % proxy haircut
    mom = _kf('6_Portfolios_ME_Prior_12_2_Daily_CSV.zip')       # SMALL LoPRIOR .. BIG HiPRIOR
    D['MTUM'] = (mom[mom.columns[5]] - fe).reindex(D.index)
    op = _kf('6_Portfolios_ME_OP_2x3_daily_CSV.zip')            # SMALL Weak .. BIG Robust
    D['QUAL'] = (op[op.columns[5]] - fe).reindex(D.index)
    for k, f in (('EFA', 'Developed_ex_US_3_Factors_Daily_CSV.zip'), ('VGK', 'Europe_3_Factors_Daily_CSV.zip'),
                 ('EWJ_P', 'Japan_3_Factors_Daily_CSV.zip')):
        x = _kf(f); s = x['Mkt-RF'] + x['RF'] - fe
        if k in D.columns and k == 'EFA':           # BE1 WIDE EFA = ACTUAL panel ETF from listing -> splice proxy before it
            a = D['EFA'].dropna(); s = pd.concat([s[s.index < a.index[0]], a]).sort_index()
        D[k if k != 'EFA' else 'EFA'] = s.reindex(D.index)
    D = D[D.index <= END].sort_index()
    D.to_pickle(fn); return D


if __name__ == '__main__':
    D = by_date()
    cov = {c: (str(D[c].first_valid_index().date()), int(D[c].notna().sum())) for c in D.columns}
    for c, v in cov.items(): print(c, v)


def by_date_ext():
    """by_date() + Treasury proxies extended back to 1953-04 from FRED monthly GS20 / GS10 (yields linearly interpolated to daily
    on the business-day calendar, then the same par / zero formulas). Used ONLY for the S&P 1955~85 check (H.15 daily starts 1962).
    Approximation: monthly yields miss intra-month moves (understates daily vol, keeps drift)."""
    fn = CACHE + 'etx_bydate_ext.pkl'
    if os.path.exists(fn): return pd.read_pickle(fn)
    D = by_date().copy()
    def mon(fn_):
        m = pd.read_csv(RAW + 'fred/' + fn_, index_col=0, parse_dates=True).iloc[:, 0].astype(float) / 100.0
        m = m[m.index <= END]
        import jp
        R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX')   # S&P trading calendar (no holiday returns lost)
        days = X.index[(X.index >= m.index[0]) & (X.index <= pd.Timestamp('1962-01-02'))]
        return m.reindex(m.index.union(days)).interpolate('time').reindex(days)
    y20 = mon('fred_GS20.csv'); y10 = mon('fred_GS10.csv')
    cut = pd.Timestamp('1962-01-02')
    ext = {'TLT': BD.bond_ret(y20, 20, 0.0015), 'IEF': BD.bond_ret(y10, 8.5, 0.0015), 'EDV': zero_ret(y20, 20, 0.0006)}
    for k, s in ext.items():
        s = s[s.index < cut]
        idx = D.index.union(s.index)
        D = D.reindex(idx)
        D.loc[s.index, k] = D.loc[s.index, k].fillna(s)
    D = D[D.index <= END].sort_index(); D.to_pickle(fn); return D
