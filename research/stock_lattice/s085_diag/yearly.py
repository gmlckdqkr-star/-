"""s0.85 vs NDX 1x by calendar year on the real NDX 1986-2014 path (MS1 engine, std.py). <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, ov
c = std.contexts()['real_ndx_86_14']
B, bfn, bp, fs = std.s085(c)
fin, EE = std.engine(c, B, bfn, bp, fs)
_, H1 = std.hold(c, 1)
n = EE.shape[1]
import jp
R_, M_ = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R_, M_, 'NDX')
idx = pd.DatetimeIndex(X.index[c.ii[0][-n:]])
lev = np.asarray(B)[0, -n:] if np.ndim(B) == 2 else np.asarray(B)[-n:]
df = pd.DataFrame({'s': EE[0], 'h': H1[0][-n:], 'lev': lev, 'r': c.r[0, -n:]}, index=idx)
y = df.groupby(df.index.year).agg(s=('s', 'last'), h=('h', 'last'), lev=('lev', 'mean'),
        vol=('r', lambda r: r.std() * np.sqrt(252)), ndx=('r', lambda r: (1 + r).prod() - 1))
y['s_ret'] = y.s.pct_change(); y['h_ret'] = y.h.pct_change()
y.loc[y.index[0], 's_ret'] = y.s.iloc[0] - 1; y.loc[y.index[0], 'h_ret'] = y.h.iloc[0] - 1
y['diff'] = y.s_ret - y.h_ret
print('cagr s0.85', fin, 'years', len(y))
print(y[['ndx', 'h_ret', 's_ret', 'diff', 'lev', 'vol']].round(3).to_string())
y.to_csv('/mnt/project-files/research/stock_lattice/s085_diag/yearly_real_ndx_86_14.csv')
