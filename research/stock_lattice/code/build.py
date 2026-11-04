"""PSL1 step 1: decision-row features and labels from the lab stock panel (lab rules via lab.stocks._Ctx).
Output: scratch npz with D, E (eligible), F (m, r1, v, h), y (raw excess next-period return), yr (raw), g, mon."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks, dsl
OUT = sys.argv[1]
P = stocks.load()
D = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
D = D[P.idx[D] >= pd.Timestamp('1970-01-02')]
cx = stocks._Ctx(P, D, {})
F = np.stack([cx.value('ret(231, 21)'), cx.value('ret(21)'), cx.value('vol(63)'), cx.value('high_dist(252)')])
age = cx.value('age()')
E = cx.E0 & (age >= 252) & np.isfinite(F).all(0)
R = P.R(stocks.H_CONS)
L = np.log1p(np.maximum(R, -0.999999))
cs = np.vstack([np.zeros((1, P.N)), np.cumsum(L, 0)])
nd = len(D); yr = np.full((nd, P.N), np.nan)
for j in range(nd - 1):
    a, b = D[j] + 3, min(D[j + 1] + 2, P.T - 1)          # rows a..b inclusive
    yr[j] = np.expm1(cs[b + 1] - cs[a])
yr[~E] = np.nan
mu = np.nanmean(yr, 1, keepdims=True)
y = yr - mu
ew = stocks.sp500ew(P)
s = pd.Series(ew); sma = s.rolling(200).mean().values
g = (ew[D] > sma[D]).astype(np.int8); gok = np.isfinite(sma[D])
mon = P.idx[D].month.values
# the holding month: execution at D+2 falls in the same calendar month as D (first trading day) -> mon
np.savez_compressed(OUT, D=D, E=E, F=F.astype(np.float32), y=y.astype(np.float32), yr=yr.astype(np.float32), g=g,
                    gok=gok, mon=mon, dates=P.idx[D].values.astype('datetime64[D]').astype(str))
print(nd, E.sum(1)[[0, 100, 300, -2]], np.nanmean(np.abs(y)), gok.argmax(), P.idx[D[gok.argmax()]])
