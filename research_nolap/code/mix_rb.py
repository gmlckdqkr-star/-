"""Yearly-rebalanced mix (generous upper bound: ignores tax realized by transfers). dev250_path only."""
import numpy as np, pandas as pd, json
from common import *
from mix import sleeve_curve, cg, streams
W = ov.WARM; C, DM = ctx_dates(); key = 'dev250_path'; c = C[key]; fin, EE = s085_daily(c)
dts = pd.DatetimeIndex(DM[key][:, W:].ravel()); rf = c.rf[:, W:]
def yf(E):  # yearly growth factors (P, Y)
    k = np.arange(251, E.shape[1], 252); v = np.c_[np.ones(E.shape[0]), E[:, k]]; return v[:, 1:] / v[:, :-1]
gs = yf(EE); base = np.median(np.prod(gs, 1) ** (1 / gs.shape[1]) - 1); out = {}
def mixrb(gl, w):
    M = np.prod((1 - w) * gs + w * gl, 1) ** (1 / gs.shape[1]) - 1; B = np.prod(gs, 1) ** (1 / gs.shape[1]) - 1
    return dict(cagr=float(np.median(M)), base=float(base), d=float(np.median(M - B)), pw=float(np.mean(M > B)))
for k in ('DEL60', 'DEL60_clip50_drop5'):
    x = streams[k].reindex(dts).values.reshape(EE.shape); x = np.where(np.isnan(x), rf, x); gl = yf(sleeve_curve(x))
    for w in (0.2, 0.4): out['%s|w%.1f' % (k, w)] = mixrb(gl, w); print(k, w, out['%s|w%.1f' % (k, w)], flush=True)
rng = np.random.default_rng(7); zn = (c.r[:, W:] - c.r[:, W:].mean()) / c.r[:, W:].std(); eps = rng.standard_normal(zn.shape)
for S in (0.5, 0.8, 1.0, 1.2, 1.5):
    for rho in (0.0, 0.3):
        x = rf + S * 0.15 / 252 + 0.15 / np.sqrt(252) * (rho * zn + np.sqrt(1 - rho ** 2) * eps); gl = yf(sleeve_curve(x))
        for w in (0.2, 0.4): out['N0 S%.1f rho%.1f|w%.1f' % (S, rho, w)] = r = mixrb(gl, w); print('N0', S, rho, w, r, flush=True)
json.dump(out, open(RES + '/mix_rb.json', 'w'), indent=1)
