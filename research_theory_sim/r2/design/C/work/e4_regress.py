"""Exploration 4: which observables carry information about the true conditional mean m(t)? (design-time use of sim latents;
seed 3, P=500, ON world). Pooled OLS of m on scale-free causal features."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F, sim
d = sim.simulate(500, H.T, 3, mechanism=True, diag=True)
m = d['diag']['m']; r = d['r']; p = d['params']
EY2 = p['Ybar'] ** 2 * (1 + 1 / p['kY'])
v = d['diag']['var_d'] + d['diag']['lam'] * EY2[:, None]
close = 100 * np.cumprod(1 + r, axis=1)
g, ok = F.logret(close)
vs = F.ewma(g ** 2, 250, ok, F.V0); vss = F.ewma(g ** 2, 1000, ok, F.V0)
feats = {}
for hf in (5, 10, 25, 60):
    feats['lvr%d' % hf] = np.log(F.ewma(g ** 2, hf, ok, F.V0) / vs)
sd = np.sqrt(vs)
cr = np.maximum(0, -g - 2.5 * sd) / sd               # crash-size in sd units
ci = (g < -2.5 * sd).astype(float)
for hl in (20, 63, 126, 250):
    feats['crs%d' % hl] = F.ewma(cr, hl, ok, 0.0) * 252
    feats['cri%d' % hl] = F.ewma(ci, hl, ok, 0.0) * 252
import scipy.ndimage as nd
lc = np.log(close)
for w in (63, 250):
    mx = nd.maximum_filter1d(lc, size=w, axis=1, origin=(w - 1) // 2)
    feats['dd%d' % w] = (lc - mx) / np.sqrt(vs * 252)
feats['lvs'] = np.log(vs / vss)
feats['ret63'] = (lc - np.roll(lc, 63, axis=1)) / np.sqrt(vs * 252)
sl = slice(400, None)
names = list(feats)
X = np.column_stack([feats[k][:, sl].ravel() for k in names] + [np.ones(m[:, sl].size)])
y = m[:, sl].ravel()
yk = (m / v)[:, sl].ravel()
lv = np.log(v / vs)[:, sl].ravel()
def ols(X, y, label):
    b, *_ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ b
    print(label, 'R2 = %.3f' % (1 - res.var() / y.var()))
    return b
b = ols(X, y, 'm on all feats:'); print('  ', dict(zip(names + ['c'], np.round(b, 4))))
for k in names:
    Xk = np.column_stack([feats[k][:, sl].ravel(), np.ones(y.size)])
    bb, *_ = np.linalg.lstsq(Xk, y, rcond=None); res = y - Xk @ bb
    bb2, *_ = np.linalg.lstsq(Xk, lv, rcond=None); res2 = lv - Xk @ bb2
    print('  single %-8s R2(m)=%.3f slope %.4f | R2(log v/vs)=%.3f' % (k, 1 - res.var() / y.var(), bb[0], 1 - res2.var() / lv.var()))
ols(X, lv, 'log(v/vs) on all feats:')
yk = np.clip(yk, -20, 20)
bk = ols(X, yk, 'm/v (clipped) on all:'); print('  ', dict(zip(names + ['c'], np.round(bk, 3))))
