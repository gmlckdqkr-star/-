import sys; sys.path.insert(0, '/tmp/claude-0/gx1verify')
from myinv import *
import beng, bk
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X); W = ov.WARM
share = np.load('/tmp/claude-0/gx1verify/us_share.npy'); g = np.nan_to_num(share, nan=-1.0) >= 0.40
i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - W; ii = np.arange(i0, len(X))[None, :]
c = ov.Ctx(X, F, ii); B, bfn, bp, fs = std.s085(c); B = np.array(B, dtype=np.float64); Bc = np.where(g[ii], np.minimum(B, 1.0), B)
feat = np.ascontiguousarray(bk.features(c))
res = {}
for nm, BB in (('v1', B), ('rule', Bc)):
    s, rec = beng.run_path(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), np.ascontiguousarray(BB[0]), feat[0], bfn, bp, fstep=fs, cspr=10.0)
    res[nm] = (s, rec)
    print(nm, 'cagr %.10f' % s['cagr'][0])
gs = g[ii][0, W:]; rec = res['rule'][1]; recv = res['v1'][1]
print('rule: max brake target on signal-on rows %.3f; max held-in-force on rows >=3 after on-onset inside on spells %.3f'
      % (rec[gs, 2].max(), rec[np.r_[np.zeros(3, bool), gs[3:] & gs[2:-1] & gs[1:-2] & gs[:-3]], 1].max()))
print('rule: any row where brake target > base b + 1e-9:', int((rec[:, 2] > rec[:, 3] + 1e-9).sum()), ' v1:', int((recv[:, 2] > recv[:, 3] + 1e-9).sum()))
d = pd.Series(np.log(rec[:, 0]) - np.log(recv[:, 0]), index=X.index[ii[0, W:]])
pts = ['1986-01-02', '1990-03-01', '1995-08-25', '1997-12-31', '2000-12-29', '2002-07-31', '2002-10-31', '2004-09-30', '2005-03-31', '2006-11-30', '2010-07-01', '2014-12-31']
prev = 0.0
for a, b in zip(pts[:-1], pts[1:]):
    x = d.loc[:b].iloc[-1]; print('%s..%s log(E_rule/E_v1) change %+.3f' % (a, b, x - prev)); prev = x
print('mean held level v1 %.3f rule %.3f (scored rows)' % (recv[:, 1].mean(), rec[:, 1].mean()))
