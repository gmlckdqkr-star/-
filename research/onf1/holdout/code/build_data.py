"""Common dataset for the overnight-futures verification (independent build from the project price panel).
Sources (all from research/data/panel_f32.npz.xz + panel_ext, Yahoo chart v8 fetched 2026-10-08 by the project):
  QQQ O/C/adj (1999-03-10..2026-10-07), ^NDX close, ^IRX (13w bill, %), ^TNX (10y, %),
  122630.KS (KODEX leverage), 114800.KS (KODEX inverse), 069500.KS (KODEX200), KRW=X, TQQQ, SPY, TLT, IEF.
Output: data/us.csv (US trading days), data/kr.csv (KR trading days). No strategy logic here.
Definitions
  US  r_cc = adj_t/adj_{t-1}-1 (total return), r_id = close/open-1, r_on = (1+r_cc)/(1+r_id)-1 (dividend falls in the night)
  futures excess: f_on = r_on - rf*dt_on, f_id = r_id - rf*dt_id; dt_on = (calendar days since prev US day - 1 + 17.5/24)/365, dt_id=(6.5/24)/365
  KR  futures night proxy kr_n = (lev_night - inv_night)/3  (lev=2f+p, inv=-f+p -> ETF open premium p and fee/cash accrual cancel)
      kr_d = (lev_day - inv_day)/3 ; kr_spot_n = 069500 open/prev close -1
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'code'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np, pandas as pd
from load_panel import sym
OUT = paths.DATA
q = sym('QQQ'); ndx = sym('_NDX'); irx = sym('_IRX'); tnx = sym('_TNX', 'panel_ext_f32.npz.xz')
us = pd.DataFrame(index=ndx.index)
us['ndx'] = ndx.close; us['ndx_open'] = ndx.open; us['ndx_high'] = ndx.high; us['ndx_low'] = ndx.low
us['rf'] = (irx.close.reindex(us.index).ffill() / 100.0)
us['y10'] = tnx.close.reindex(us.index).ffill()
us['y3m'] = irx.close.reindex(us.index).ffill()
us['qqq_open'] = q.open.reindex(us.index); us['qqq_close'] = q.close.reindex(us.index); us['qqq_adj'] = q.adj.reindex(us.index)
us['qqq_high'] = q.high.reindex(us.index); us['qqq_low'] = q.low.reindex(us.index)
r_cc = us.qqq_adj / us.qqq_adj.shift() - 1; r_id = us.qqq_close / us.qqq_open - 1
us['r_cc'] = r_cc; us['r_id'] = r_id; us['r_on'] = (1 + r_cc) / (1 + r_id) - 1
us['ndx_cc'] = us.ndx / us.ndx.shift() - 1
gap = pd.Series(us.index, index=us.index).diff().dt.days.fillna(1)
us['caldays'] = gap
us['dt_on'] = (gap - 1 + 17.5 / 24) / 365; us['dt_id'] = (6.5 / 24) / 365
rfp = us.rf.shift().fillna(us.rf)
us['f_on'] = us.r_on - rfp * us.dt_on; us['f_id'] = us.r_id - rfp * us.dt_id
tq = sym('TQQQ'); us['tqqq_adj'] = tq.adj.reindex(us.index)
spy = sym('SPY'); us['spy_open'] = spy.open.reindex(us.index); us['spy_close'] = spy.close.reindex(us.index); us['spy_adj'] = spy.adj.reindex(us.index)
for k in ('TLT', 'IEF'):
    d = sym(k); us[k.lower() + '_adj'] = d.adj.reindex(us.index)
us.index.name = 'date'; us.to_csv(OUT + 'us.csv', float_format='%.8g')

l = sym('122630.KS'); i = sym('114800.KS'); k = sym('069500.KS')
idx = k.index.union(l.index).union(i.index)
kr = pd.DataFrame(index=idx)
for nm, d in (('k', k), ('lev', l), ('inv', i)):
    d = d.reindex(idx)                      # raw rows incl. NaN rows: a night across a missing day stays NaN
    kr[nm + '_open'] = d.open; kr[nm + '_close'] = d.close
    kr[nm + '_n'] = d.open / d.close.shift() - 1; kr[nm + '_d'] = d.close / d.open - 1
kr['kr_n'] = (kr.lev_n - kr.inv_n) / 3; kr['kr_d'] = (kr.lev_d - kr.inv_d) / 3
kr['kr_spot_n'] = kr.k_n
fx = sym('KRW_X'); kr['usdkrw'] = fx.close.reindex(idx, method='ffill')
kr.index.name = 'date'; kr.to_csv(OUT + 'kr.csv', float_format='%.8g')
print('US', us.index[0].date(), us.index[-1].date(), len(us), 'QQQ rows', us.r_on.notna().sum())
print('KR', kr.index[0].date(), kr.index[-1].date(), len(kr), 'kr_n rows', kr.kr_n.notna().sum(), 'first', kr.kr_n.first_valid_index().date())
# gaps check: KR NaN-row dates in the panel (dropped)
print('KR rows with lev close NaN after 2010-03:', int(kr.loc['2010-03':].lev_close.isna().sum()))
