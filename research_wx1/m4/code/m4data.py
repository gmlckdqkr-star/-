"""WX1-M4 data: daily unlevered base returns of the M4 asset universe, every source cut at 2014-12-31 right after reading.
Conventions (PRECOMMIT_M4 section 2):
  - era-matched equity convention = MS1's own: before 1986-01-02 the NDX slot is S&P 500 TR (MS1 real_spx bases), and KF
    equity proxies are total return; from 1986-01-02 NDX is the price index (MS1) and every equity proxy is made price-only
    (KF monthly total minus ex-dividend return, spread evenly over the month's trading days).
  - KF equity proxies: -0.8 %/yr proxy haircut on the base (BE1 overlap finding), fees by product in m4eng.
  - Treasuries: synthetic par-bond TR from H.15 CMT (BE1 bdata method). Gold: XAU/USD spot (1985-). Cash: MS1 cash.
Output: data/m4_base.pkl = dict(U=DataFrame base returns (NaN = not available), UTR=TR version for inverse products,
        rf, cash, bench (1x NDX MS1), macro flags, maxL, meta)."""
import io, os, sys, zipfile, json, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
END = pd.Timestamp('2014-12-31'); SPLIT = pd.Timestamp('1986-01-02')
BKF = '/mnt/project-files/research/broad_etf/data/raw/kf/'
DL = S + 'dl/'
HC = 0.008 / 252          # KF proxy haircut per day


def kf(path, section=0, daily=True):
    z = zipfile.ZipFile(path); txt = z.read(z.namelist()[0]).decode('latin1').splitlines()
    nd = 8 if daily else 6
    blocks, cur = [], None
    for ln in txt:
        p = [x.strip() for x in ln.split(',')]
        if len(p) > 1 and p[0] == '' and cur is None: cur = {'cols': p[1:], 'rows': []}; continue
        if cur is not None:
            if len(p) > 1 and p[0].isdigit() and len(p[0]) == nd: cur['rows'].append(p)
            else: blocks.append(cur); cur = None
    if cur: blocks.append(cur)
    b = blocks[section]
    fmt = '%Y%m%d' if daily else '%Y%m'
    df = pd.DataFrame([r[1:] for r in b['rows']], index=pd.to_datetime([r[0] for r in b['rows']], format=fmt),
                      columns=b['cols']).astype(float)
    df = df[df.index <= END]                                   # seal first
    return df.where(df > -99.0) / 100.0


def h15():
    df = pd.read_csv('/mnt/project-files/research/broad_etf/data/raw/h15/H15_all_daily.csv', skiprows=5, index_col=0, na_values=['ND', ''])
    df.index = pd.to_datetime(df.index); df = df[df.index <= END]
    df.columns = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
    return df.astype(float) / 100.0


def bond_ret(y, M):
    """par-bond TR from CMT yield (decimal), maturity M years (BE1 bdata.bond_ret without fee)"""
    y = y.dropna(); dt = y.index.to_series().diff().dt.days.fillna(1).values / 365.0
    y0 = y.shift(1).values; dy = y.diff().values; c = y0 / 2
    D = (1 - (1 + c) ** (-2 * M)) / np.maximum(y0, 1e-6)
    C = 2 * D ** 2
    r = y0 * dt - D * dy + 0.5 * C * dy ** 2
    return pd.Series(r, index=y.index).iloc[1:]


# sector map: name -> (kf file key, column, max leverage of a real US ETF, real ETF tickers)
SECT = {
    'TECH': ('k12', 'BusEq', 3, 'TECL/ROM/XLK'), 'SEMI': ('k49', 'Chips', 3, 'SOXL/USD/SOXX'),
    'FIN': ('k12', 'Money', 3, 'FAS/UYG/XLF'), 'HLTH': ('k12', 'Hlth', 3, 'CURE/RXL/XLV'),
    'ENER': ('k12', 'Enrgy', 3, 'ERX/DIG/XLE'), 'REIT': ('k49', 'RlEst', 3, 'DRN/URE/IYR'),
    'UTIL': ('k12', 'Utils', 3, 'UTSL/UPW/XLU'), 'INDU': ('k12', 'Manuf', 3, 'DUSL/UXI/XLI'),
    'DISC': ('k12', 'Shops', 3, 'WANT/UCC/XLY'), 'RETL': ('k49', 'Rtail', 3, 'RETL/XRT'),
    'HOME': ('k49', 'Cnstr', 3, 'NAIL/ITB'), 'BANK': ('k49', 'Banks', 3, 'DPST/KRE'),
    'BIO': ('k49', 'Drugs', 3, 'LABU/XBI(proxy=pharma)'), 'TRAN': ('k49', 'Trans', 3, 'TPOR/IYT'),
    'AERO': ('k49', 'Aero', 3, 'DFEN/ITA'), 'GOLDM': ('k49', 'Gold', 3, 'NUGT/GDX'),
    'MATL': ('k12', 'Chems', 2, 'UYM/XLB'), 'STAP': ('k12', 'NoDur', 2, 'UGE/XLP'), 'TELE': ('k12', 'Telcm', 2, 'LTL/IYZ'),
}


def build():
    B = pd.read_pickle(S + 'data/ms1_base.pkl')               # MS1 loader output (<= 2014), from m4_std_dump.py
    B = B[B.index <= END]
    k12d = kf(BKF + '12_Industry_Portfolios_daily_CSV.zip'); k49d = kf(BKF + '49_Industry_Portfolios_daily_CSV.zip')
    k6d = kf(BKF + '6_Portfolios_2x3_daily_CSV.zip')
    k12t = kf(DL + '12_Industry_Portfolios_CSV.zip', daily=False); k12x = kf(DL + '12_Industry_Portfolios_Wout_Div_CSV.zip', daily=False)
    k49t = kf(DL + '49_Industry_Portfolios_CSV.zip', daily=False); k49x = kf(DL + '49_Industry_Portfolios_Wout_Div_CSV.zip', daily=False)
    k6t = kf(DL + '6_Portfolios_2x3_CSV.zip', daily=False); k6x = kf(DL + '6_Portfolios_2x3_Wout_Div_CSV.zip', daily=False)
    mom = kf(DL + '10_Portfolios_Prior_12_2_Daily_CSV.zip'); op = kf(DL + 'Portfolios_Formed_on_OP_Daily_CSV.zip')
    bm = kf(DL + 'Portfolios_Formed_on_BE-ME_Daily_CSV.zip')
    for d in (k12d, k49d, k6d, k12t, k12x, k49t, k49x, k6t, k6x, mom, op, bm):
        d.columns = [c.strip() for c in d.columns]
    # calendar = KF daily dates 1962-01-02 .. 2014-12-31 intersected with MS1 base calendar
    idx = B.index[(B.index >= pd.Timestamp('1962-01-02')) & (B.index <= END)]
    idx = idx.intersection(k12d.index)
    mkey = idx.to_period('M')
    ndays = pd.Series(1, index=idx).groupby(mkey).transform('sum').values

    def div_daily(tot, exd, col):
        dv = (tot[col] - exd[col]).clip(lower=0.0)              # monthly dividend return
        dv.index = dv.index.to_period('M')
        return pd.Series(dv.reindex(mkey).values / ndays, index=idx).fillna(0.0)

    def eq_series(daily_tr, div):
        """era-matched: TR before 1986-01-02, price-only (TR - spread dividend) after; minus haircut"""
        tr = daily_tr.reindex(idx)
        px = tr - div
        out = tr.where(idx < SPLIT, px) - HC
        return out, tr - HC

    U, UTR, meta = {}, {}, {}
    # NDX slot and SPX
    spx_tr = B['SPX'].reindex(idx); ndx = B['NDX'].reindex(idx)
    U['NDX'] = spx_tr.where(idx < SPLIT, ndx)
    UTR['NDX'] = spx_tr.where(idx < SPLIT, ndx + 0.008 / 252)  # NDX dividend ~0.8 %/yr assumed for the inverse leg
    sys.path.insert(0, '/mnt/project-files/research/lab'); from lab import data as LD
    g = LD.series('_GSPC'); g = g[g.index <= END]
    gr = g.pct_change().reindex(idx)
    U['SPX'] = spx_tr.where(idx < SPLIT, gr)
    UTR['SPX'] = spx_tr
    meta['NDX'] = 'pre-1986 S&P500 TR (MS1 real_spx), 1986+ NDX price (MS1); TQQQ/QLD/QQQ/PSQ'
    meta['SPX'] = 'pre-1986 S&P500 TR, 1986+ ^GSPC price; UPRO/SSO/SPY/SH'
    for nm, (fk, col, L, tick) in SECT.items():
        d = k12d if fk == 'k12' else k49d; t, x = (k12t, k12x) if fk == 'k12' else (k49t, k49x)
        U[nm], UTR[nm] = eq_series(d[col], div_daily(t, x, col))
        meta[nm] = 'KF%s %s VW; %s' % (fk[1:], col, tick)
    c6 = list(k6d.columns)[:3]                                  # SMALL LoBM, ME1 BM2, SMALL HiBM
    sm = k6d[c6].mean(axis=1)
    dv = sum(div_daily(k6t, k6x, c) for c in c6) / 3.0
    U['SMALL'], UTR['SMALL'] = eq_series(sm, dv); meta['SMALL'] = 'KF 6pf small avg (Russell2000 proxy); TNA/UWM/IWM/RWM'
    mdiv = sum(div_daily(k12t, k12x, c) for c in ['NoDur', 'Durbl', 'Manuf', 'Enrgy', 'Chems', 'BusEq', 'Telcm', 'Utils', 'Shops', 'Hlth', 'Money', 'Other']) / 12.0
    U['MOM'], UTR['MOM'] = eq_series(mom['Hi PRIOR'], mdiv); meta['MOM'] = 'KF top decile prior 12-2 VW, 1x only (MTUM, real 2013-04)'
    U['QUAL'], UTR['QUAL'] = eq_series(op['Hi 30'], mdiv); meta['QUAL'] = 'KF top 30% OP VW, 1x only (QUAL, real 2013-07)'
    U['VAL'], UTR['VAL'] = eq_series(bm['Hi 30'], mdiv); meta['VAL'] = 'KF top 30% BE/ME VW, 1x only (VLUE, real 2013-04)'
    h = h15()
    lt = bond_ret(h['y20'], 20); lt30 = bond_ret(h['y30'], 25)
    ltb = pd.concat([lt[lt.index < pd.Timestamp('1977-02-16')], lt30[(lt30.index >= pd.Timestamp('1977-02-16'))]]).sort_index()
    ltb = ltb[~ltb.index.duplicated(keep='last')]
    ltb = ltb.combine_first(lt)
    U['LTB'] = ltb.reindex(idx); UTR['LTB'] = U['LTB']; meta['LTB'] = 'H.15 CMT 20y (1962-77) / 30y (1977-) par bond TR; TMF/UBT/TLT/TBF'
    U['MTB'] = bond_ret(h['y10'], 8.5).reindex(idx); UTR['MTB'] = U['MTB']; meta['MTB'] = 'H.15 10y CMT, 8.5y par bond TR; TYD/UST/IEF'
    gd = pd.concat([pd.read_csv('/mnt/project-files/research/broad_etf/data/raw/gold/xauusd_td_1985_1998.csv', sep=';', index_col=0, parse_dates=True)['close'],
                    pd.read_csv('/mnt/project-files/research/data/gold/xauusd_twelvedata_1day_raw.csv', sep=';', index_col=0, parse_dates=True)['close']])
    gd = gd[~gd.index.duplicated(keep='last')].sort_index(); gd = gd[gd.index <= END]
    gl = gd.reindex(idx.union(gd.index)).ffill().reindex(idx)
    gr = gl.pct_change(); gr[gl.shift(1).isna()] = np.nan
    U['GOLD'] = gr; UTR['GOLD'] = gr; meta['GOLD'] = 'XAU/USD spot (1985-); UGL/GLD'
    U = pd.DataFrame(U, index=idx); UTR = pd.DataFrame(UTR, index=idx)
    rf = B['rf'].reindex(idx).fillna(0.0)
    cash = np.maximum(rf - 0.02 / 252, 0.0) * (1 - 0.154)
    bench = U['NDX'] - 0.002 / 252
    mf = pd.read_csv('/mnt/project-files/research/lab/lab/macro_flags_le2014.csv.gz', index_col=0, parse_dates=True)
    mf = mf[mf.index <= END]
    mf = mf[((mf['cal'] == 'spx') & (mf.index < SPLIT)) | ((mf['cal'] == 'ndx') & (mf.index >= SPLIT))]   # lab MACRO_SPLICE rule
    mf = mf[~mf.index.duplicated(keep='last')].drop(columns=['cal']).reindex(idx).ffill().fillna(0).astype(bool)
    maxL = {k: 3 for k in U.columns}
    for k in ('MATL', 'STAP', 'TELE', 'GOLD'): maxL[k] = 2
    for k in ('MOM', 'QUAL', 'VAL'): maxL[k] = 1
    inv_ok = ['NDX', 'SPX', 'SMALL', 'LTB']
    D = dict(U=U, UTR=UTR, rf=rf, cash=cash, bench=bench, macro=mf, maxL=maxL, inv_ok=inv_ok, meta=meta)
    pd.to_pickle(D, S + 'data/m4_base.pkl')
    return D


if __name__ == '__main__':
    D = build(); U = D['U']
    print(U.index[0], U.index[-1], len(U))
    print(U.apply(lambda s: s.first_valid_index()).to_string())
    for a, b in (('1964-01-01', '1985-12-31'), ('1986-01-01', '1999-12-31')):
        x = U[(U.index >= a) & (U.index <= b)]
        print(a, b); print(((1 + x).prod() ** (252 / x.count()) - 1).round(3).to_string())
