"""M1 (WX1) primitive data: one daily calendar 1928-01-03..2014-12-31 (Ken French dates, as std/jp), every primitive
aligned to what was public at close t (publication lags below). <=2014 only: every loader slices <= SEAL right after
reading; nothing after 2014-12-31 is used.
Lag rules (PRECOMMIT_M1 sec.2): daily market series: same day (Treasury/VIX/KF) or +1 day (FRED daily H.15/H.10 style);
monthly macro without a genuine release date: first trading day of month m+2; ALFRED genuine first release (vintage date
within 120 days of the observation period start): the first trading day >= realtime_start; earnings/book-based
valuation (e/p, d/p, b/m, CAPE): m+3; quarterly: quarter end + 3 months (first trading day of q_end_month+4).
Output: cache/prim.npz with dates, era-independent primitives (name -> float64 array, NaN = unknown) + meta json."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/nb')
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, jp, mkt  # noqa: E402  (std puts the chassis folders on sys.path)

SEAL = pd.Timestamp('2014-12-31')
R_ = '/mnt/project-files/research/'
SCR = '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/'


def cal():
    R, M = jp.calendar('1928-01-03', '2014-12-31')
    assert R.index.max() <= SEAL
    return R, M


STALE = 130   # days: a value not refreshed for longer than this is unknown (series ended / gap); quarterly uses 230


def stale_cut(idx, out, limit):
    """forward-fill 'out' (NaN = no update that day) but blank values whose last update is older than limit days."""
    upd = pd.Series(np.where(np.isfinite(out), idx.values.astype('datetime64[D]').astype(np.int64), np.nan), index=idx).ffill().values
    v = pd.Series(np.asarray(out, float), index=idx).ffill().values.copy()
    age = idx.values.astype('datetime64[D]').astype(np.int64) - upd
    v[~(age <= limit)] = np.nan
    return v


def _first_td_on_or_after(idx, when):
    """position in idx of the first trading day >= when (vectorized)."""
    return idx.searchsorted(pd.DatetimeIndex(when))


def place(idx, avail_dates, values):
    """step series on calendar idx: value v_j is known from the first trading day >= avail_j (later obs override)."""
    out = np.full(len(idx), np.nan)
    a = pd.DatetimeIndex(avail_dates); v = np.asarray(values, float)
    o = np.argsort(a.values, kind='stable'); a = a[o]; v = v[o]
    pos = _first_td_on_or_after(idx, a)
    for p, x in zip(pos, v):
        if p < len(idx) and np.isfinite(x):
            out[p] = x
    return stale_cut(idx, out, STALE)


def monthly_m2(idx, s, lag_months=2):
    """monthly series indexed by month start (obs month m) -> known from first trading day of month m+lag."""
    s = s[s.index <= SEAL].dropna()
    av = s.index + pd.offsets.MonthBegin(lag_months)
    return place(idx, av, s.values)


def alfred_first(path, obs_col, val_col, rt_col, idx, lag_months=2, genuine_days=120, obs_le=SEAL):
    """ALFRED real-time file -> earliest-vintage value per observation, available at the genuine first release date
    (realtime_start within genuine_days of the period start) else first trading day of month m+lag (conservative)."""
    d = pd.read_csv(path)
    d[obs_col] = pd.to_datetime(d[obs_col]); d[rt_col] = pd.to_datetime(d[rt_col].astype(str).str[:10], errors='coerce')
    d = d[(d[obs_col] <= obs_le) & (d[rt_col] <= SEAL)]
    d[val_col] = pd.to_numeric(d[val_col], errors='coerce')
    d = d.dropna(subset=[val_col]).sort_values([obs_col, rt_col]).groupby(obs_col).first()
    obs = d.index; rt = d[rt_col]
    fallback = obs + pd.offsets.MonthBegin(lag_months)
    genuine = (rt - obs).dt.days <= genuine_days
    av = pd.DatetimeIndex(np.where(genuine, rt, fallback))
    av = pd.DatetimeIndex(np.minimum(av.values, fallback.values)) if False else av
    return place(idx, av, d[val_col].values), pd.Series(d[val_col].values, index=obs)


def daily_series(idx, s, lag_days=0):
    s = s[s.index <= SEAL].dropna(); s = s[~s.index.duplicated(keep='last')]
    if lag_days:
        pos = idx.searchsorted(s.index) + lag_days        # value of date d usable at close of the lag_days-th trading day after
        out = np.full(len(idx), np.nan); ok = pos < len(idx)
        out[pos[ok]] = s.values[ok]
        return stale_cut(idx, out, 30)
    return stale_cut(idx, s.reindex(idx).values, 30)


def yoy_monthly(s):
    """12-month log change of a monthly positive series indexed by obs month."""
    s = s.sort_index(); return np.log(s / s.shift(12))


def build():
    R, M = cal(); idx = R.index
    P = {}; meta = {}

    def add(name, arr, kind, freq, src, c3=False):
        a = np.asarray(arr, float)
        assert a.shape == (len(idx),), name
        P[name] = a
        f = np.flatnonzero(np.isfinite(a))
        meta[name] = dict(kind=kind, freq=freq, src=src, c3=c3, first=str(idx[f[0]].date()) if len(f) else None)

    # ---- rates / credit (std frame columns, already lagged as in mkt.macro) ----
    add('y3m', M['y3m'].values, 'rate', 'd', 'std frame: ^IRX daily (TB3MS monthly m+1 before 1970)')
    add('y10', M['y10'].values, 'rate', 'd', 'std frame: ^TNX daily (Shiller GS10 monthly m+1 before)')
    add('curve', (M['y10'] - M['y3m']).values, 'rate', 'd', 'y10 - y3m')
    fvx = mkt.pser('_FVX', 3, 'panel_ext_f32.npz.xz'); add('y5', daily_series(idx, fvx), 'rate', 'd', 'panel ^FVX')
    tyx = mkt.pser('_TYX', 3, 'panel_ext_f32.npz.xz'); add('y30', daily_series(idx, tyx), 'rate', 'd', 'panel ^TYX')
    add('cs', M['cs'].values, 'rate', 'd', 'std frame: DBAA-DAAA daily lag1 (BAA-AAA monthly m+1 before 1986)')
    # ---- volatility / options ----
    vix = mkt.pser('_VIX', 3, 'panel_ext_f32.npz.xz'); vixd = daily_series(idx, vix)
    add('vix', vixd, 'pos', 'd', 'panel ^VIX (1990-)')
    spx = R['SPX'].fillna(0.0).values
    rv21 = pd.Series(np.log1p(spx), index=idx).rolling(21).std().values * np.sqrt(252) * 100
    add('vrp', vixd - rv21, 'rate', 'd', 'VIX - 21d realized vol of S&P (1990-)')
    sk = pd.read_csv(R_ + 'clean_a/data_optsent/clean_le2014/SKEW.csv', parse_dates=['date']).set_index('date')['value']
    add('skew', daily_series(idx, sk, lag_days=0), 'pos', 'd', 'Cboe SKEW clean_a (1990-)')
    # ---- Ken French industries / size (daily returns known at close) ----
    ind = ['TECH', 'FIN', 'ENER', 'HLTH', 'UTIL', 'STAP', 'MANU', 'SHOP', 'TELE']
    lr = {k: np.log1p(R[k].fillna(0.0).values) for k in ind + ['SMALL', 'MICRO', 'SPX']}
    cum = {k: np.cumsum(v) for k, v in lr.items()}
    m21 = np.vstack([pd.Series(cum[k]).diff(21).values for k in ind])
    add('kf_disp', np.nanstd(m21, axis=0), 'pos', 'd', 'x-sect std of 21d log returns, 9 KF industries')
    ab = np.vstack([(cum[k] - pd.Series(cum[k]).rolling(200).mean().values) > 0 for k in ind]).astype(float)
    ab[:, :200] = np.nan
    add('kf_breadth', np.nanmean(ab, axis=0), 'rate', 'd', 'share of 9 KF industries above own 200d mean')
    add('small_rs', cum['SMALL'] - cum['SPX'], 'rate', 'd', 'log cum KF size quintile 2 / S&P TR')
    add('micro_rs', cum['MICRO'] - cum['SPX'], 'rate', 'd', 'log cum KF Lo20 size / S&P TR')
    add('defcyc_rs', 0.5 * (cum['UTIL'] + cum['STAP']) - 0.5 * (cum['TECH'] + cum['MANU']), 'rate', 'd', 'defensive (Utils+NoDur) vs cyclical (BusEq+Manuf)')
    for k in ('FIN', 'ENER', 'TECH'):
        add(k.lower() + '_rs', cum[k] - cum['SPX'], 'rate', 'd', 'log cum KF %s / S&P TR' % k)
    # ---- FX ----
    kr = pd.read_csv(R_ + 'data/fx_dexkous/clean/DEXKOUS_clean.csv')
    kr.columns = [c.lower() for c in kr.columns]
    dc = [c for c in kr.columns if 'date' in c][0]; vc = [c for c in kr.columns if c != dc][0]
    krs = pd.Series(pd.to_numeric(kr[vc], errors='coerce').values, index=pd.to_datetime(kr[dc])).dropna()
    # KRW (DEXKOUS clean starts 1993-01): < 5 active discovery years after the 2y quantile warm-up -> not used (PRECOMMIT_M1)
    a27 = R_ + 'data/a27_macro_vintage/merged/'
    tw, _ = alfred_first(a27 + 'alfred_DTWEXM_full.csv', 'obs_date', 'value', 'realtime_start', idx, genuine_days=30)
    add('usd', tw, 'pos', 'd', 'ALFRED DTWEXM first vintage (1973-)')
    # ---- labor / activity / prices (ALFRED first release) ----
    cl = pd.read_csv(R_ + 'clean_a/data_macro_n/ALFRED_ICNSA_realtime_le2014.csv', parse_dates=['period_start_date'])
    cl['rt'] = pd.to_datetime(cl['realtime_start_date']); cl = cl[(cl['period_start_date'] <= SEAL) & (cl['rt'] <= SEAL)]
    cl = cl.sort_values(['period_start_date', 'rt']).groupby('period_start_date').first()
    c4 = cl['ICNSA'].astype(float).rolling(4).mean(); cy = np.log(c4 / c4.shift(52))
    gen = (cl['rt'] - cl.index).dt.days <= 14
    av = pd.DatetimeIndex(np.where(gen, cl['rt'], cl.index + pd.Timedelta(days=7)))
    add('claims_yoy', place(idx, av, cy.values), 'rate', 'w', 'ALFRED ICNSA 4wk avg yoy log (release date or week end +7d)')
    for nm, fn, tr, desc in [('cpi_yoy', 'CPIAUCNS', 'yoy', 'CPI NSA yoy'), ('core_yoy', 'CPILFESL', 'yoy', 'core CPI yoy'),
                             ('ip_yoy', 'INDPRO', 'yoy', 'industrial production yoy'), ('pay_yoy', 'PAYEMS', 'yoy', 'payrolls yoy'),
                             ('unrate', 'UNRATE', 'lvl', 'unemployment rate'), ('houst', 'HOUST', 'log', 'housing starts (log)'),
                             ('permit', 'PERMIT', 'log', 'building permits (log)'), ('neword', 'NEWORDER', 'yoy', 'core capital goods new orders yoy'),
                             ('tcu', 'TCU', 'lvl', 'capacity utilization'), ('fedfunds', 'FEDFUNDS', 'lvl', 'fed funds (monthly avg)'),
                             ('oil_yoy', 'OILPRICE', 'yoy', 'oil price (FRED OILPRICE) yoy')]:
        f = a27 + 'alfred_%s_full.csv' % fn
        if not os.path.exists(f):
            continue
        d = pd.read_csv(f); d['obs_date'] = pd.to_datetime(d['obs_date']); d['realtime_start'] = pd.to_datetime(d['realtime_start'], errors='coerce')
        d = d[(d['obs_date'] <= SEAL) & (d['realtime_start'] <= SEAL)]
        d['value'] = pd.to_numeric(d['value'], errors='coerce'); d = d.dropna(subset=['value'])
        g = d.sort_values(['obs_date', 'realtime_start']).groupby('obs_date').first()
        v = g['value']
        if tr == 'yoy': v = yoy_monthly(v)
        elif tr == 'log': v = np.log(v)
        gen = (g['realtime_start'] - g.index).to_series(index=g.index).dt.days <= 120 if False else ((g['realtime_start'] - g.index).dt.days <= 120)
        fb = g.index + pd.offsets.MonthBegin(2)
        av = pd.DatetimeIndex(np.where(gen, g['realtime_start'], fb))
        add(nm, place(idx, av, v.values), 'rate', 'm', 'ALFRED %s first vintage, %s' % (fn, desc))
    m2 = pd.read_csv(R_ + 'clean_regime/data/ALFRED_M2SL_realtime_le2014.csv', parse_dates=['period_start_date'])
    m2['rt'] = pd.to_datetime(m2['realtime_start_date']); m2 = m2[(m2['period_start_date'] <= SEAL) & (m2['rt'] <= SEAL)]
    g = m2.sort_values(['period_start_date', 'rt']).groupby('period_start_date').first()
    v = yoy_monthly(g['M2SL'].astype(float)); gen = (g['rt'] - g.index).dt.days <= 120
    av = pd.DatetimeIndex(np.where(gen, g['rt'], g.index + pd.offsets.MonthBegin(2)))
    add('m2_yoy', place(idx, av, v.values), 'rate', 'm', 'ALFRED M2SL first vintage yoy (1971-)')
    add('realrate', M['y3m'].values - 100 * P['cpi_yoy'], 'rate', 'm', 'y3m - CPI yoy')
    um = pd.read_csv(R_ + 'clean_regime/data/FRED_UMCSENT_le2014.csv', parse_dates=['observation_date']).set_index('observation_date')['UMCSENT']
    add('umich', monthly_m2(idx, pd.to_numeric(um, errors='coerce'), 2), 'pos', 'm', 'UMich sentiment m+2 (1978-)')
    ph = pd.read_csv(R_ + 'open_data/raw/fred_GACDFSA066MSFRBPHI.csv', parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0]
    add('philly', monthly_m2(idx, pd.to_numeric(ph, errors='coerce'), 2), 'rate', 'm', 'Philly Fed general activity m+2 (1968-)')
    ph2 = pd.read_csv(R_ + 'open_data/raw/fred_NOCDFSA066MSFRBPHI.csv', parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0]
    add('philly_no', monthly_m2(idx, pd.to_numeric(ph2, errors='coerce'), 2), 'rate', 'm', 'Philly Fed new orders m+2 (1968-)')
    # ---- valuation / GWZ monthly (no full-sample-estimated variables) ----
    cc = mkt.shiller_cpi_cape(); cc = cc[cc.index <= SEAL]
    add('cape', monthly_m2(idx, cc['cape'], 3), 'pos', 'm', 'Shiller CAPE m+3')
    gz = pd.read_excel(R_ + 'open_data/raw/goyal_welch_zafirov_2024.xlsx', sheet_name='Monthly')
    gz['d'] = pd.to_datetime(gz['yyyymm'].astype(int).astype(str), format='%Y%m'); gz = gz[gz['d'] <= SEAL].set_index('d')
    gz = gz.apply(pd.to_numeric, errors='coerce')
    gwz = [('dp', 'd/p', 3, 'rate', True), ('ep', 'e/p', 3, 'rate', True), ('bm', 'b/m', 3, 'rate', False), ('ntis', 'ntis', 2, 'rate', False),
           ('dfr', 'dfr', 2, 'rate', False), ('ltr', 'ltr', 2, 'rate', False), ('lzrt', 'lzrt', 2, 'rate', False),
           ('ndrbl', 'ndrbl', 2, 'rate', False), ('skvw', 'skvw', 2, 'rate', False), ('tail', 'tail', 2, 'rate', False),
           ('rdsp', 'rdsp', 2, 'rate', False), ('avgcor', 'avgcor', 2, 'rate', False), ('ygap', 'ygap', 2, 'rate', False),
           ('disag', 'disag', 2, 'rate', False), ('csp', 'csp', 2, 'rate', False)]
    for nm, col, lag, kind, logit in gwz:
        if nm in ('dp', 'ep'):
            # BT1 fix (ADDENDUM_BT1_2): e12/d12 are linearly interpolated between quarter-end anchors (Shiller), so a
            # monthly m+3 lag leaks the next quarter. Point-in-time: latest quarter-end e12/d12 known by then
            # (quarter-end month + 4) over the month-m index price (known at month end -> first trading day of m+1).
            fld = 'e12' if nm == 'ep' else 'd12'
            q = gz[fld].where(gz.index.month.isin([3, 6, 9, 12])).dropna()
            avail = q.copy(); avail.index = q.index + pd.offsets.MonthBegin(4)          # Mar obs -> known Jul 1
            pm = gz['price'].dropna(); pm.index = pm.index + pd.offsets.MonthBegin(1)    # month m price -> m+1
            known = avail.reindex(avail.index.union(pm.index)).ffill().reindex(pm.index)
            s = np.log(known / pm).dropna()
            add('gwz_' + nm, place(idx, s.index, s.values), kind, 'm', 'GWZ2024 PIT log(%s quarter-end, +4m)/price(m, +1m)' % fld)
            continue
        s = gz[col].dropna()
        if logit: s = np.log(s)
        add('gwz_' + nm, monthly_m2(idx, s, lag), kind, 'm', 'GWZ2024 %s m+%d' % (col, lag))
    # ltr / dfr are monthly returns: cumulate into level index so changes = trailing returns
    for nm in ('gwz_ltr', 'gwz_dfr'):
        col = 'ltr' if nm == 'gwz_ltr' else 'dfr'
        s = np.log1p(gz[col].dropna()).cumsum()
        add(nm, monthly_m2(idx, s, 2), 'rate', 'm', 'GWZ2024 cumulated %s (level index) m+2' % col)
    q = pd.read_excel(R_ + 'open_data/raw/goyal_welch_zafirov_2024.xlsx', sheet_name='Quarterly')
    q = q[['yyyyq', 'i/k']].dropna(); y = (q['yyyyq'] // 10).astype(int); qq = (q['yyyyq'] % 10).astype(int)
    qend = pd.to_datetime(dict(year=y, month=qq * 3, day=1))
    s = pd.Series(pd.to_numeric(q['i/k'], errors='coerce').values, index=qend); s = s[s.index <= SEAL]
    global STALE
    STALE = 230
    add('gwz_ik', place(idx, s.index + pd.offsets.MonthBegin(4), s.values), 'rate', 'q', 'GWZ2024 i/k quarterly +3m')
    STALE = 130
    # C3-family price-derived GWZ (S&P variance, Dow 52w/all-time high distance)
    for nm, col in (('gwz_svar', 'svar'), ('gwz_dtoy', 'dtoy'), ('gwz_dtoat', 'dtoat')):
        add(nm, monthly_m2(idx, gz[col].dropna(), 2), 'rate', 'm', 'GWZ2024 %s m+2 (price-derived: C3 family)' % col, c3=True)
    # ---- IPO (Ritter) ----
    ip = pd.read_csv(R_ + 'clean_b/infra/ipo/RITTER_IPOALL_current_1975_2014.csv')
    ip['d'] = pd.to_datetime(dict(year=ip['year'], month=ip['month'], day=1)); ip = ip.set_index('d')
    n = pd.to_numeric(ip['gross_number'], errors='coerce'); n12 = n.rolling(12).sum()
    add('ipo_n12', monthly_m2(idx, np.log1p(n12), 2), 'rate', 'm', 'Ritter IPO count trailing 12m (log1p) m+2 (1976-)')
    fr = pd.to_numeric(ip['avg_first_day_return_pct'], errors='coerce').rolling(6, min_periods=3).mean()
    add('ipo_ret6', monthly_m2(idx, fr, 2), 'rate', 'm', 'Ritter IPO first-day return 6m avg m+2')
    # ---- commodities (World Bank CMO monthly) ----
    cm = pd.read_excel(R_ + 'open_data/raw/CMO_monthly.xlsx', sheet_name='Monthly Prices', header=None, skiprows=6)
    cm = cm[cm[0].astype(str).str.match(r'^\d{4}M\d{2}$')]
    cm.index = pd.to_datetime(cm[0].str.replace('M', '-') + '-01'); cm = cm[cm.index <= SEAL]
    oil = pd.to_numeric(cm[1], errors='coerce'); cu = pd.to_numeric(cm[64], errors='coerce'); au = pd.to_numeric(cm[69], errors='coerce')
    add('wb_oil', monthly_m2(idx, np.log(oil), 2), 'rate', 'm', 'World Bank crude oil avg (log) m+2')
    add('wb_copper', monthly_m2(idx, np.log(cu), 2), 'rate', 'm', 'World Bank copper (log) m+2')
    add('wb_gold', monthly_m2(idx, np.log(au), 2), 'rate', 'm', 'World Bank gold (log) m+2')
    add('wb_cuau', monthly_m2(idx, np.log(cu / au), 2), 'rate', 'm', 'copper/gold (log) m+2')
    # ---- AQR century premia (monthly returns, constructed after the fact: flagged) ----
    aq = pd.read_csv(R_ + 'salon/data/aqr_century_allmacro_le2014.csv', skiprows=1, parse_dates=['date']).set_index('date')
    aq = aq[aq.index <= SEAL]
    for c in ('MULTI', 'MOM'):
        s = np.log1p(pd.to_numeric(aq[c], errors='coerce').dropna()).cumsum(); s.index = s.index.to_period('M').to_timestamp()
        add('aqr_' + c.lower(), monthly_m2(idx, s, 2), 'rate', 'm', 'AQR century %s cumulated m+2 (backtest-constructed)' % c)
    return idx, P, meta


if __name__ == '__main__':
    idx, P, meta = build()
    for k, m in meta.items():
        a = P[k]; f = np.isfinite(a)
        l = np.flatnonzero(f); m['last'] = str(idx[l[-1]].date()) if len(l) else None
        print('%-12s %-4s %-3s c3=%d first=%s last=%s n=%d' % (k, m['kind'], m['freq'], m['c3'], m['first'], m['last'], f.sum()))
    np.savez_compressed(SCR + 'cache/prim.npz', dates=idx.values.astype('datetime64[D]').astype(np.int64), **P)
    json.dump(meta, open(SCR + 'cache/prim_meta.json', 'w'), indent=1)
    print(len(P), 'primitives, calendar', idx[0].date(), idx[-1].date(), len(idx))
