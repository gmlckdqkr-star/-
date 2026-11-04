"""GT data loader. Every series is cut at 2014-12 before anything else. Monthly, index = pandas Period('M')."""
import numpy as np, pandas as pd, xlrd
KF = '/mnt/project-files/research/data/ken_french/raw/mirror_a91quaini/'
SH = '/mnt/project-files/research/data/macro_regime/raw/SHILLER_ie_data_IA_20141222172333.xls'
MN = '/mnt/project-files/research/data/macro_n/raw/'
SPXD = '/mnt/project-files/research/data/deep_history/clean/SPX_TR_daily_1927_2014.csv'
END = pd.Period('2014-12', 'M')

def _kf(fn):
    df = pd.read_csv(KF + fn)
    df = df[df['Date'].astype(str).str.match(r'^\d{6}$')]
    idx = pd.PeriodIndex([pd.Period(f'{str(d)[:4]}-{str(d)[4:]}', 'M') for d in df['Date']])
    df = df.drop(columns='Date').astype(float); df.index = idx; df.columns = [c.strip() for c in df.columns]
    df = df[df.index <= END].replace(-99.99, np.nan) / 100.0
    return df

def load():
    ind = _kf('17_Industry_Portfolios.CSV')
    ff = _kf('F-F_Research_Data_Factors.CSV')
    rf = ff['RF']; mkt = ff['Mkt-RF'] + ff['RF']; hml = ff['HML']
    fac = pd.DataFrame(index=ff.index)
    op = _kf('25_Portfolios_ME_OP_5x5.CSV'); be = _kf('25_Portfolios_ME_BETA_5x5.csv'); bm = _kf('25_Portfolios_5x5.CSV')
    p12 = _kf('25_Portfolios_ME_Prior_12_2.CSV'); p1 = _kf('25_Portfolios_ME_Prior_1_0.CSV')
    fac['BIG_HiOP'] = op['BIG HiOP']; fac['BIG_LoBETA'] = be['BIG LoBETA']; fac['BIG_HiBM'] = bm['BIG HiBM']
    fac['BIG_LoBM'] = bm['BIG LoBM']; fac['BIG_HiPRIOR'] = p12['BIG HiPRIOR']; fac['BIG_LoREV'] = p1['BIG LoPRIOR']
    # Shiller (2014-12-22 vintage)
    s = xlrd.open_workbook(SH).sheet_by_name('Data'); rows = []
    for r in range(8, s.nrows):
        v = s.row_values(r)
        if not isinstance(v[0], float): continue
        y = int(v[0]); m = int(round((v[0] - y) * 100)); m = 10 if m == 1 and abs(v[0] - y - 0.1) < 1e-6 else m
        f = lambda x: float(x) if isinstance(x, float) else np.nan
        rows.append((pd.Period(f'{y}-{m:02d}', 'M'), f(v[1]), f(v[2]), f(v[3]), f(v[4]), f(v[6])))
    sh = pd.DataFrame(rows, columns=['p', 'P', 'D', 'E', 'CPI', 'GS10']).set_index('p'); sh = sh[sh.index <= END]
    sh = sh[~sh.index.duplicated()]
    baa = pd.read_csv(MN + 'BAA.csv'); aaa = pd.read_csv(MN + 'AAA.csv')
    for d in (baa, aaa): d.index = pd.PeriodIndex(pd.to_datetime(d.iloc[:, 0]), freq='M')
    spread = (baa.iloc[:, 1] - aaa.iloc[:, 1]); spread = spread[spread.index <= END]
    idx = ind.index
    # CAPE and macro states computed on the FULL Shiller history (1871~), then aligned. Lags: E 6 months, CPI 1 month.
    E6 = sh['E'].shift(6); CPI1 = sh['CPI'].shift(1)
    realE = E6 / CPI1; realP = sh['P'] / CPI1
    sh['CAPE'] = realP / realE.rolling(120).mean()
    sh['CAPE_med240'] = sh['CAPE'].shift(1).rolling(240, min_periods=120).median()
    g = realE / realE.shift(12) - 1; sh['grow_up'] = (g > g.shift(6)).astype(float).where(g.notna() & g.shift(6).notna())
    pi = CPI1 / CPI1.shift(12) - 1; sh['infl_up'] = (pi > pi.shift(12)).astype(float).where(pi.notna() & pi.shift(12).notna())
    sh = sh.reindex(idx); spread = spread.reindex(idx)
    # 10y bond total return from GS10 (duration 7.5), known same month (market rate)
    y = sh['GS10'] / 100.0
    bond = (y.shift(1) / 12 + 7.5 * (y.shift(1) - y))
    dy = (sh['D'] / sh['P'])            # dividend yield (annual), used only for withholding drag
    return dict(ind=ind, fac=fac.reindex(idx), rf=rf.reindex(idx), mkt=mkt.reindex(idx), hml=hml.reindex(idx),
                sh=sh, spread=spread, bond=bond, dy=dy.ffill())

def spx_daily():
    d = pd.read_csv(SPXD, parse_dates=['date']).set_index('date'); d = d[d.index <= '2014-12-31']
    return d['tr_ret'].fillna(0.0)
