"""Reviewer check of input timing only: is the chain's 10-year yield a same-day value? Correlation between two INPUT series
(the chain's bond proxy v.c.rb and the TLT fund return) at lags -1, 0, +1. No candidate, no v1, no account figure."""
import sys
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(['ret:TLT', 'ret:IEF'], X.index))
rb = v.c.rb[0]; dy = np.r_[np.nan, np.diff(v.m['y10'])]
for key in ('ret:TLT', 'ret:IEF'):
    a = v.x[key]
    for lag in (-1, 0, 1):
        x = -dy[1:-1]; y = a[1 + lag:len(a) - 1 + lag]; ok = ~(np.isnan(x) | np.isnan(y))
        print(key, 'corr(-dy10[t], fund[t%+d]) = %.2f  (pairs %d)' % (lag, np.corrcoef(x[ok], y[ok])[0, 1], int(ok.sum())))
