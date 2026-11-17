"""FRESH1: parse Ken French files, cut at 2014-12-31 immediately, save one npz.
Usage: python -I prep_french.py <dir with csv> <out.npz>"""
import sys, io, numpy as np, pandas as pd
D = sys.argv[1]; OUT = sys.argv[2]; CUT = 20141231


def section(path, title, daily=True):
    L = open(path, encoding='latin-1').read().splitlines()
    i = next(k for k, s in enumerate(L) if s.strip().startswith(title))
    j = i + 2
    while j < len(L) and L[j].strip() and L[j].strip()[0].isdigit(): j += 1
    df = pd.read_csv(io.StringIO('\n'.join(L[i + 1:j])), index_col=0)
    df.columns = [c.strip() for c in df.columns]
    df = df[df.index <= (CUT if daily else CUT // 100)]          # cut BEFORE anything else
    return df


d12 = section(D + '/12_Industry_Portfolios_Daily.csv', 'Average Value Weighted Returns -- Daily')
d49 = section(D + '/49_Industry_Portfolios_Daily.csv', 'Average Value Weighted Returns -- Daily')
m12 = section(D + '/12_Industry_Portfolios.csv', 'Average Value Weighted Returns -- Monthly', daily=False)
x12 = section(D + '/12_Industry_Portfolios_Wout_Div.csv', 'Average Value Weighted Returns -- Monthly', daily=False)
L = open(D + '/F-F_Research_Data_Factors_daily.csv', encoding='latin-1').read().splitlines()
i = next(k for k, s in enumerate(L) if s.startswith(',Mkt-RF'))
j = i + 1
while j < len(L) and L[j].strip() and L[j].strip()[0].isdigit(): j += 1
ff = pd.read_csv(io.StringIO('\n'.join(L[i:j])), index_col=0); ff.columns = [c.strip() for c in ff.columns]; ff = ff[ff.index <= CUT]
assert d12.index.max() <= CUT and d49.index.max() <= CUT and ff.index.max() <= CUT and m12.index.max() <= CUT // 100
assert (d12.index == ff.index).all() and (d49.index == ff.index).all()
d12 = d12.where(d12 > -99); d49 = d49.where(d49 > -99); m12 = m12.where(m12 > -99); x12 = x12.where(x12 > -99)
np.savez_compressed(OUT, dates=d12.index.values.astype(np.int64), names12=np.array(d12.columns), r12=d12.values / 100,
                    names49=np.array(d49.columns), r49=d49.values / 100, mkt=(ff['Mkt-RF'].values + ff['RF'].values) / 100, rf=ff['RF'].values / 100,
                    months=m12.index.values.astype(np.int64), m12=m12.values / 100, x12=x12.reindex(m12.index).values / 100)
print('days', len(d12), d12.index.min(), d12.index.max(), 'months', len(m12), m12.index.min(), m12.index.max())
print('12 names', list(d12.columns)); print('49 NaN share by col (top)', d49.isna().mean().sort_values(ascending=False).head(8).round(3).to_dict())
dv = (m12 - x12.reindex(m12.index)); print('mean yearly dividend return by industry 1955-85 / 1986-2014 (%):')
print((dv[(dv.index >= 195501) & (dv.index <= 198512)].mean() * 1200).round(2).to_dict()); print((dv[(dv.index >= 198601)].mean() * 1200).round(2).to_dict())
