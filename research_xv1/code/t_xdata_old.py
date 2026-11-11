"""<= 2014 only: alignment of the instrument inputs and model-vs-actual 3x funds on the old calendar."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, xdata
c, dates = xv1.build(xv1.OLD_END); idx = c.idx; r = c.r[0]; rf = c.rf[0]
print('rows', len(idx), idx[0].date(), idx[-1].date())
se = xdata.semis(idx); ch = xdata.chips(idx); sx = xdata.ret('SOXX', idx)
print('chips NaN days', int(np.isnan(ch).sum()), '| SOXX first valid', idx[np.argmax(~np.isnan(sx))].date(), '| semis NaN', int(np.isnan(se).sum()))
m = ~np.isnan(sx) & ~np.isnan(ch)
print('SOXX vs KF Chips 2001-07..2014: corr %.3f, ann mean %.2f%% vs %.2f%%, ann vol %.1f%% vs %.1f%%' % (np.corrcoef(sx[m], ch[m])[0, 1], 25200 * sx[m].mean(), 25200 * ch[m].mean(), 100 * sx[m].std() * 252 ** .5, 100 * ch[m].std() * 252 ** .5))
for key, base in (('TQQQ', r), ('SOXL', se)):
    a = xdata.ret(key, idx); mod = xdata.lev3(np.nan_to_num(base), rf); k = ~np.isnan(a)
    yrs = k.sum() / 252
    print('%s actual vs model %s..2014: ann log %.2f%% vs %.2f%% (gap %+.2f pp/yr), daily corr %.4f' % (key, idx[np.argmax(k)].date(),
          100 * np.log1p(a[k]).sum() / yrs, 100 * np.log1p(mod[k]).sum() / yrs, 100 * (np.log1p(a[k]).sum() - np.log1p(mod[k]).sum()) / yrs, np.corrcoef(a[k], mod[k])[0, 1]))
