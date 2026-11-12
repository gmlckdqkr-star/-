import sys; sys.path.insert(0, '/tmp/claude-0/gx1verify')
from myinv import *
R, M = jp.calendar('1984-01-03', '2014-12-31'); cal = R.index
share, den, K, units, per = inv_share(cal, 'US')
for d in ['1990-03-02', '1992-06-01', '1995-08-25', '1995-08-28', '1998-01-02', '1999-06-01', '2000-12-29', '2001-01-02', '2007-06-01', '2010-07-01', '2010-07-02']:
    t = cal.searchsorted(pd.Timestamp(d))
    v = [m for m in units if per[m][1][t]]; tr = [m for m in v if per[m][0][t]]
    print(cal[t].date(), 'share %.3f den %d' % (share[t], den[t]), 'valid', v, 'true', tr)
