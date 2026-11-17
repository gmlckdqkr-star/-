"""Reviewer check: is v.c.vix[0] the same-day VIX close (aligned with lvl:_VIX3M@ext)? Counts of equal rows only."""
import sys
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
X = xv1.frame(xv1.OLD_END)
for nm in ('lvl:_VIX@ext', 'lvl:_VIX'):
    try:
        E = xv1.extras([nm], X.index); v = xv1.View(X, E); a = v.c.vix[0]; b = v.x[nm]
        ok = ~np.isnan(a) & ~np.isnan(b)
        if not ok.any(): print(nm, 'no overlapping rows'); continue
        same = lambda p, q: int((np.abs(p - q) < 1e-3 * np.abs(q))[~np.isnan(p) & ~np.isnan(q)].sum())
        print(nm, 'rows both', int(ok.sum()), 'equal same row', same(a, b), 'equal chain[t] vs panel[t-1]', same(a[1:], b[:-1]), 'equal chain[t] vs panel[t+1]', same(a[:-1], b[1:]))
    except Exception as ex: print(nm, 'not available:', type(ex).__name__, str(ex)[:100])
