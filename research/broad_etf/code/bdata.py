"""research/broad_etf (thread '더 넓은 ETF로 최고 방법 넘기', 2026-11-04). <=2014 ONLY: every source is cut at 2014-12-31 first.
By-date daily simple returns of the broad ETF universe.
U_LONG (proxy before listing, ACTUAL ETF after listing; usable on every MS1 basis that its data covers):
  KF 12 industries VW (sector ETFs), KF49 VW Gold/Chips/Softw/Drugs/Banks/RlEst, KF 6 portfolios 2x3 (size/style ETFs),
  KF market (VTI), US Treasuries synthetic from H.15 CMT (TLT/IEF/SHY), gold spot XAU/USD (GLD).
  Proxy fee: equity 0.40 %/yr, bonds 0.15 %/yr, gold 0.40 %/yr (subtracted daily). ACTUAL panel ETF replaces the proxy from listing.
U_WIDE (ACTUAL only, from listing; real-history checks only): country/EM/intl, credit, TIPS, commodities from research/data panel.
Survivorship: the panel holds ETFs alive at fetch time (no delisted ETFs). Proxies before listing are category indexes (no survivor pick)."""
import io, os, zipfile, lzma, numpy as np, pandas as pd
END = pd.Timestamp('2014-12-31')
RAW = '/mnt/project-files/research/broad_etf/data/raw/'
CACHE = '/tmp/claude-0/broad_etf_cache/'; os.makedirs(CACHE, exist_ok=True)

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
    df = df[df.index <= END]
    return df.where(df > -99.0) / 100.0

def _h15():
    df = pd.read_csv(RAW + 'h15/H15_all_daily.csv', skiprows=5, index_col=0, na_values=['ND', ''])
    df.index = pd.to_datetime(df.index); df = df[df.index <= END]
    df.columns = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
    return df.astype(float) / 100.0

def bond_ret(y, M, fee):
    """par-bond total return from CMT yield y (decimal), maturity M years: carry + duration + convexity, actual day count"""
    y = y.dropna(); dt = y.index.to_series().diff().dt.days.fillna(1).values / 365.0
    y0 = y.shift(1).values; dy = y.diff().values; c = y0 / 2
    D = (1 - (1 + c) ** (-2 * M)) / np.maximum(y0, 1e-6)           # modified duration (semiannual par bond)
    C = 2 * D ** 2                                                 # crude convexity (small term)
    r = y0 * dt - D * dy + 0.5 * C * dy ** 2 - fee * dt
    return pd.Series(r, index=y.index).iloc[1:]

def _panel():
    import sys; sys.path.insert(0, '/mnt/project-files/research/lab'); from lab import data as LD
    return LD

def panel_ret(key):
    LD = _panel(); s = LD.series(key); s = s[s.index <= END]
    return s.pct_change().dropna()

def splice(proxy, actual):
    """proxy before the first ACTUAL return date, ACTUAL after"""
    if actual is None or len(actual) == 0: return proxy
    a0 = actual.index[0]
    return pd.concat([proxy[proxy.index < a0], actual]).sort_index()

KF12 = {'XLP': 'NoDur', 'DUR': 'Durbl', 'XLI': 'Manuf', 'XLE': 'Enrgy', 'XLB': 'Chems', 'XLK': 'BusEq', 'TEL': 'Telcm',
        'XLU': 'Utils', 'XLY': 'Shops', 'XLV': 'Hlth', 'XLF': 'Money'}
KF49 = {'GDX': 'Gold', 'SOXX': 'Chips', 'IGV': 'Softw', 'PJP': 'Drugs', 'KBE': 'Banks', 'IYR': 'RlEst'}
ACT = {'XLP': 'XLP', 'XLI': 'XLI', 'XLE': 'XLE', 'XLB': 'XLB', 'XLK': 'XLK', 'XLU': 'XLU', 'XLY': 'XLY', 'XLV': 'XLV',
       'XLF': 'XLF', 'GDX': 'GDX', 'SOXX': 'SOXX', 'IGV': 'IGV', 'KBE': 'KBE', 'IYR': 'IYR', 'IWM': 'IWM', 'IWN': 'IWN',
       'IWD': 'IWD', 'IWF': 'IWF', 'VTI': 'VTI', 'TLT': 'TLT', 'IEF': 'IEF', 'SHY': 'SHY', 'GLD': 'GLD'}
WIDE = ['EFA', 'EEM', 'EWJ', 'EWG', 'EWU', 'EWC', 'EWA', 'EWZ', 'EWT', 'EWY', 'FXI', 'VWO', 'TIP', 'LQD', 'HYG', 'EMB', 'AGG',
        'DBC', 'SLV', 'USO', 'DBA', 'MDY', 'RSP', 'XBI', 'IBB', 'OIH', 'XME', 'IYT', 'VNQ', 'ITB']
LONG = list(KF12) + list(KF49) + ['IWM', 'IWN', 'IWD', 'IWF', 'VTI', 'TLT', 'IEF', 'SHY', 'GLD']
CLASS = {**{k: 'eq' for k in list(KF12) + list(KF49) + ['IWM', 'IWN', 'IWD', 'IWF', 'VTI']}, 'TLT': 'bd', 'IEF': 'bd', 'SHY': 'bd',
         'GLD': 'cm', 'GDX': 'eq'}
DEF = ['TLT', 'IEF', 'GLD', 'XLU', 'XLP', 'XLV']

def by_date(actual=True):
    fn = CACHE + 'bydate_%d.pkl' % int(actual)
    if os.path.exists(fn): return pd.read_pickle(fn)
    k12 = _kf('12_Industry_Portfolios_daily_CSV.zip'); k49 = _kf('49_Industry_Portfolios_daily_CSV.zip')
    k6 = _kf('6_Portfolios_2x3_daily_CSV.zip'); ff = _kf('F-F_Research_Data_Factors_daily_CSV.zip')
    fe = 0.012 / 252; out = {}   # 0.4 % fee + 0.8 % proxy-vs-ACTUAL haircut (equity proxies ran +0.8 pp/yr above ETFs on overlap)
    for k, c in KF12.items(): out[k] = k12[c] - fe
    for k, c in KF49.items(): out[k] = k49[c] - fe
    c6 = list(k6.columns)   # SMALL LoBM, ME1 BM2, SMALL HiBM, BIG LoBM, ME2 BM2, BIG HiBM
    out['IWM'] = k6[c6[:3]].mean(axis=1) - fe; out['IWN'] = k6[c6[2]] - fe
    out['IWD'] = k6[c6[5]] - fe; out['IWF'] = k6[c6[3]] - fe
    out['VTI'] = ff['Mkt-RF'] + ff['RF'] - fe
    h = _h15()
    lt = bond_ret(h['y20'], 20, 0.0015); lt30 = bond_ret(h['y30'], 25, 0.0015)
    lt = pd.concat([lt30[(lt30.index < lt.index[0]) | (lt30.index < pd.Timestamp('1993-10-02'))], lt[lt.index >= pd.Timestamp('1993-10-02')]]).sort_index()
    lt = lt[~lt.index.duplicated(keep='last')]
    l10 = bond_ret(h['y20'], 20, 0.0015); lt = lt.combine_first(l10)
    out['TLT'] = lt; out['IEF'] = bond_ret(h['y10'], 8.5, 0.0015); out['SHY'] = bond_ret(h['y2'], 2, 0.0015)
    g = pd.concat([pd.read_csv(RAW + 'gold/xauusd_td_1985_1998.csv', sep=';', index_col=0, parse_dates=True)['close'],
                   pd.read_csv('/mnt/project-files/research/data/gold/xauusd_twelvedata_1day_raw.csv', sep=';', index_col=0, parse_dates=True)['close']])
    g = g[~g.index.duplicated(keep='last')].sort_index(); g = g[g.index <= END]
    out['GLD'] = g.pct_change().dropna() - 0.004 / 252
    if actual:
        for k, a in ACT.items(): out[k] = splice(out[k], panel_ret(a))
        for k in WIDE: out[k] = panel_ret(k)
    D = pd.DataFrame(out).sort_index(); D = D[D.index <= END]
    D.to_pickle(fn); return D
