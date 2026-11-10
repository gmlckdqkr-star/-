"""Extend data/us.csv past 2026-10-07 with QQQ daily bars from Twelve Data (fetched 2026-11-10, data/td_qqq_*.csv) and
Alpha Vantage daily Treasury yields (data/av_y10_tail.csv, av_y3m_tail.csv).  Output data/us_ext.csv.
The extension rows are a PROXY for NDX level (ndx = last ndx * QQQ close ratio; no QQQ dividend in the window) and are used
only for the 'through 2026-11-09' information rows, never for design or MS1."""
import numpy as np, pandas as pd
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'code'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
D = paths.DATA
us = pd.read_csv(D + 'us.csv', index_col=0, parse_dates=True)
q = pd.read_csv(D + 'td_qqq_20260925_20261109.csv', index_col=0, parse_dates=True)
ov = q.index.intersection(us.index)
print('overlap rows', len(ov), 'max abs diff open %.4f close %.4f' % ((q.open[ov] - us.qqq_open[ov]).abs().max(), (q.close[ov] - us.qqq_close[ov]).abs().max()))
y10 = pd.read_csv(D + 'av_y10_tail.csv', index_col=0, parse_dates=True).iloc[:, 0]
y3m = pd.read_csv(D + 'av_y3m_tail.csv', index_col=0, parse_dates=True, na_values='.').iloc[:, 0].sort_index()
off = (us.y3m - y3m).dropna().iloc[-5:].mean(); print('y3m offset (IRX discount vs CMT) %.3f' % off)
new = q.index[q.index > us.index[-1]]
last = us.iloc[-1]; ext = pd.DataFrame(index=new, columns=us.columns, dtype=float)
ext['qqq_open'] = q.open[new]; ext['qqq_close'] = q.close[new]; ext['qqq_adj'] = q.close[new] * (last.qqq_adj / last.qqq_close)
ext['qqq_high'] = q.high[new]; ext['qqq_low'] = q.low[new]
ext['ndx'] = last.ndx * q.close[new] / last.qqq_close; ext['ndx_open'] = last.ndx * q.open[new] / last.qqq_close
ext['y10'] = y10.reindex(new).ffill().fillna(last.y10) if True else np.nan
ext['y3m'] = (y3m.reindex(new) + off).ffill().fillna(last.y3m); ext['rf'] = ext.y3m / 100
a = pd.concat([us, ext]); a['y10'] = a.y10.ffill()
r_cc = a.qqq_adj / a.qqq_adj.shift() - 1; r_id = a.qqq_close / a.qqq_open - 1
a['r_cc'] = r_cc; a['r_id'] = r_id; a['r_on'] = (1 + r_cc) / (1 + r_id) - 1; a['ndx_cc'] = a.ndx / a.ndx.shift() - 1
gap = pd.Series(a.index, index=a.index).diff().dt.days.fillna(1); a['caldays'] = gap
a['dt_on'] = (gap - 1 + 17.5 / 24) / 365; a['dt_id'] = (6.5 / 24) / 365
rfp = a.rf.shift().fillna(a.rf); a['f_on'] = a.r_on - rfp * a.dt_on; a['f_id'] = a.r_id - rfp * a.dt_id
chk = (a.loc[us.index, ['r_cc', 'r_id', 'r_on', 'f_on', 'f_id']] - us[['r_cc', 'r_id', 'r_on', 'f_on', 'f_id']]).abs().max().max()
print('recomputed old rows max abs diff %.2e' % chk)
a.index.name = 'date'; a.to_csv(D + 'us_ext.csv', float_format='%.8g')
print(a[['ndx', 'y10', 'y3m', 'qqq_open', 'qqq_close', 'r_on', 'r_id']].tail(24).round(4).to_string())
print('QQQ 10-07 -> 11-05 close %.1f%%, -> 11-09 %.1f%%' % ((a.qqq_close['2026-11-05'] / a.qqq_close['2026-10-07'] - 1) * 100, (a.qqq_close.iloc[-1] / a.qqq_close['2026-10-07'] - 1) * 100))
