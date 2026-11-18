import os, sys, numpy as np, pandas as pd
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5lib as L, df5data as DD, df5run as R
from dfctx import std
iv = std.iv; jp = std.jp
a, b, P, blk, seed = iv.POOLS['dev250']; X, S = L._src(a, b, 'NDX')
lv = np.cumprod(1 + X['r'].fillna(0).values); Dd = X.index; n = len(X)
pos = lambda d: int(Dd.searchsorted(pd.Timestamp(d)))
amax = lambda x, y: pos(x) + int(np.argmax(lv[pos(x):pos(y)])); amin = lambda x, y: pos(x) + int(np.argmin(lv[pos(x):pos(y)]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
for p_, t_ in ((pk1, tr1), (pk2, tr2), (pk3, tr3)):
    print('excl', str(Dd[p_])[:10], '->', str(Dd[min(t_ + 250, n - 1)])[:10], 'trough', str(Dd[t_])[:10], 'dd %.3f' % (lv[t_] / lv[p_] - 1))
print('n', n, 'first', str(Dd[0])[:10])
# share of source days covered by X paths, and 2-sample stats
for wn in ('P', 'X'):
    pan = DD.panel(wn); w = L.world(wn); ii = w['ii'][:, 300:]
    q = pan['QQQ'][0][:, 300:]; s = pan['SPX'][0][:, 300:]; lt = pan['LTT'][0][:, 300:]; d3 = pan['DEF3'][0][:, 300:]; g = pan['GOLD'][0][:, 300:]
    def c21(x, y):
        k = (x.shape[1] // 21) * 21
        xx = np.log1p(x[:, :k]).reshape(x.shape[0], -1, 21).sum(2).ravel(); yy = np.log1p(y[:, :k]).reshape(y.shape[0], -1, 21).sum(2).ravel()
        return np.corrcoef(xx, yy)[0, 1]
    print(wn, 'means QQQ %.4f SPX %.4f DEF3 %.4f LTT %.4f' % (q.mean() * 252, s.mean() * 252, d3.mean() * 252, lt.mean() * 252),
          'corr21 QQQ-LTT %.3f QQQ-GOLD %.3f QQQ-DEF3 %.3f' % (c21(q, lt), c21(q, g), c21(q, d3)),
          'yrs-coverage 1986-99 share %.3f' % (np.mean(S.index.values[ii] < np.datetime64('2000-01-01'))))
    # conditional: LTT 21d return when QQQ 21d return < -10%
    k = (q.shape[1] // 21) * 21
    qq = np.log1p(q[:, :k]).reshape(q.shape[0], -1, 21).sum(2).ravel(); ll = np.log1p(lt[:, :k]).reshape(q.shape[0], -1, 21).sum(2).ravel()
    m = qq < -0.10
    print('   months QQQ<-10%%: share %.3f, mean LTT in those %.4f, mean LTT otherwise %.4f' % (m.mean(), ll[m].mean(), ll[~m].mean()))
    L._WORLDS.pop(wn, None); DD._P.clear()
