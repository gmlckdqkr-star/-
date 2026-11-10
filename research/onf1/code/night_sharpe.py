"""Stand-alone night-only 1x MNQ on <=2014 data (price night = QQQ open / previous close - 1, financing = T-bill + 0.4%p over
the night's calendar time, fee per side charged twice a day).  -> results/night_sharpe_le2014.json
Project gate for a new non-timing return stream (tools/idea_check/idea_check.py): same-basis stand-alone Sharpe >= 0.55."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np, pandas as pd
us = pd.read_csv(paths.CUT + 'us_le2014.csv', index_col=0, parse_dates=True)
q = us.dropna(subset=['qqq_open', 'qqq_close']).copy()
on = q.qqq_open / q.qqq_close.shift() - 1; rf = q.rf.shift().fillna(q.rf); dt = q.dt_on
res = {}
def line(lab, a, b, fee=0.000083, s=0.004):
    x = (on - (rf + s) * dt - 2 * fee).loc[a:b].dropna(); g = (on - rf * dt).loc[a:b].dropna()
    r = dict(gross_excess_yr=float(g.mean() * 252), gross_sharpe=float(g.mean() / g.std() * np.sqrt(252)), net_yr=float(x.mean() * 252),
             net_vol=float(x.std() * np.sqrt(252)), net_sharpe=float(x.mean() / x.std() * np.sqrt(252)), net_t=float(x.mean() / x.std() * np.sqrt(len(x))), n=int(len(x)))
    res[lab] = r
    print('%-22s gross excess %5.1f%%/yr (Sharpe %.2f) | after fee %.2fbp x2 and +0.4%%p: %5.1f%%/yr, vol %.1f%%, Sharpe %.2f, t %.1f' % (
        lab, r['gross_excess_yr'] * 100, r['gross_sharpe'], fee * 1e4, r['net_yr'] * 100, r['net_vol'] * 100, r['net_sharpe'], r['net_t']))
W = (('1999-03-11', '2014-12-31'), ('2001-01-01', '2014-12-31'), ('2005-01-01', '2014-12-31'), ('1999-03-11', '2000-12-31'), ('2001-01-01', '2004-12-31'), ('2005-01-01', '2007-12-31'), ('2008-01-01', '2014-12-31'))
for a, b in W: line(a[:4] + '..' + b[:4], a, b)
for a, b in W[:3]:
    line(a[:4] + '..' + b[:4] + ' fee x2', a, b, fee=0.000166); line(a[:4] + '..' + b[:4] + ' fee 0.30bp', a, b, fee=0.00003)
json.dump(res, open(paths.RES + 'night_sharpe_le2014.json', 'w'), indent=1)
