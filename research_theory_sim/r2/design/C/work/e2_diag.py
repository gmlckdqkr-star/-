"""Exploration 2: where is the expected return in the ON world? m(t) and variance by observable state (seed 1, P=500)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F, sim
d = sim.simulate(500, H.T, 1, mechanism=True, diag=True)
m = d['diag']['m']; r = d['r']; rf = d['rf']
close = 100 * np.cumprod(1 + r, axis=1)
g, ok = F.logret(close)
x = r - rf
vf = F.ewma(g ** 2, 20, ok, F.V0); vs = F.ewma(g ** 2, 250, ok, F.V0)
W = 300
# realised forward 21d excess return and variance, by vf/vs ratio bins
fwd = np.full_like(x, np.nan)
cs = np.cumsum(x, axis=1)
fwd[:, :-22] = cs[:, 22:] - cs[:, 1:-21]
fv = np.full_like(x, np.nan); cs2 = np.cumsum(x ** 2, axis=1); fv[:, :-22] = cs2[:, 22:] - cs2[:, 1:-21]
ratio = vf / vs
sl = slice(W, -22)
R = ratio[:, sl].ravel(); M = m[:, sl].ravel(); FW = fwd[:, sl].ravel(); FV = fv[:, sl].ravel(); VF = vf[:, sl].ravel()
qs = np.percentile(R, [0, 20, 40, 60, 80, 95, 100])
print('bins of vf/vs (hl20 / hl250):')
for a, b in zip(qs[:-1], qs[1:]):
    k = (R >= a) & (R < b)
    print('  [%.2f,%.2f) m/yr %.3f fwd21 ann %.3f fwdvar ann %.4f  -> kelly %.2f ; vf ann %.4f' % (a, b, M[k].mean(), FW[k].mean() * 252 / 21, FV[k].mean() * 252 / 21, FW[k].mean() / FV[k].mean(), VF[k].mean() * 252))
# by drawdown from 250d high
lc = np.log(close)
mx = np.full_like(lc, np.nan)
from numpy.lib.stride_tricks import sliding_window_view
for i in range(0, lc.shape[0]):
    pass
# rolling max via cummax of 250 window (approx using blocks)
import scipy.ndimage as nd
mx = nd.maximum_filter1d(lc, size=250, axis=1, origin=124)
dd = (lc - mx)[:, sl].ravel()
qs = np.percentile(dd, [0, 5, 10, 25, 50, 75, 100])
print('bins of drawdown from 250d max:')
for a, b in zip(qs[:-1], qs[1:]):
    k = (dd >= a) & (dd < b)
    print('  [%.3f,%.3f) m/yr %.3f fwd21 ann %.3f fwdvar ann %.4f -> kelly %.2f' % (a, b, M[k].mean(), FW[k].mean() * 252 / 21, FV[k].mean() * 252 / 21, FW[k].mean() / FV[k].mean()))
# joint: ratio low/high x dd shallow/deep
for nm, kr in (('vf/vs<1', R < 1), ('vf/vs>=1', R >= 1)):
    for nd_, kd in (('dd>-5%', dd > -0.05), ('-15<dd<-5', (dd <= -0.05) & (dd > -0.15)), ('dd<-15%', dd <= -0.15)):
        k = kr & kd
        print('  %s %s frac %.3f m %.3f fwd %.3f fvar %.4f kelly %.2f' % (nm, nd_, k.mean(), M[k].mean(), FW[k].mean() * 12, FV[k].mean() * 12, FW[k].mean() / FV[k].mean()))
