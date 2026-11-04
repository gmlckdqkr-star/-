"""Overlap (daily corr with s0.85 on real NDX 1986-2014) + mixing a sleeve next to s0.85 under MS1 bases.
Two accounts, split w at start, no rebalance (conservative: s0.85 deduction scaled by 1-w, sleeve none).
Sleeve on path: daily net returns by date, yearly 22% tax on positive gain every 252 path days + final.
N0 synthetic: rf + S*vol/252 + vol/sqrt(252)*(rho*z_ndx + sqrt(1-rho^2)*eps)."""
import numpy as np, pandas as pd, json
from common import *
import fomc
W = ov.WARM
C, DM = ctx_dates()
z = np.load(RES + '/n2_streams.npz'); sd = pd.to_datetime(z['dates'], unit='D')
names = ['DEL60', 'DEL60_clip50_drop5', 'DEL120', 'ADD60']
streams = {k: pd.Series(z[k], index=sd) for k in names}

def sleeve_curve(ret):   # ret (P,T) daily net
    P, T = ret.shape; E = np.ones(P); start = np.ones(P); out = np.zeros((P, T))
    for t in range(T):
        if t > 0 and t % 252 == 0: g = E - start; E = E - 0.22 * np.maximum(g, 0); start = E.copy()
        E = E * (1 + ret[:, t]); out[:, t] = E
    g = E - start; out[:, -1] = E - 0.22 * np.maximum(g, 0); return out

def cg(E): return np.maximum(E[:, -1], 1e-9) ** (252 / E.shape[1]) - 1
res = {}
for key in ('real_ndx_86_14', 'dev250_path'):
    c = C[key]; fin, EE = s085_daily(c); dts = pd.DatetimeIndex(DM[key][:, W:].ravel())
    rf = c.rf[:, W:]; base = np.median(cg(EE))
    if key == 'real_ndx_86_14':
        s85 = EE[0, 1:] / EE[0, :-1] - 1; ndx = c.r[0, W + 1:]
        F = fomc.flags_for(DM[key], fomc_days(), 1); B = 3 * shift_left(F, 3)
        _, EF = std.engine(c, B, std.ident, np.zeros(1), 0.5); f1s = EF[0, 1:] / EF[0, :-1] - 1
        cor = {'F1S': float(np.corrcoef(f1s, s85)[0, 1])}
        for k, s in streams.items():
            x = s.reindex(dts).fillna(0).values.reshape(EE.shape)[0, 1:]; cor[k] = float(np.corrcoef(x, s85)[0, 1]); cor[k + '_vsNDX'] = float(np.corrcoef(x, ndx)[0, 1])
        res['corr_vs_s085_daily'] = cor; print('corr', cor, flush=True)
    for k, s in streams.items():
        x = s.reindex(dts).values.reshape(EE.shape); x = np.where(np.isnan(x), rf, x)   # missing dates -> raw rf (generous)
        Es = sleeve_curve(x)
        for w in (0.1, 0.2, 0.3):
            M = (1 - w) * EE + w * Es; d = cg(M) - cg(EE)
            res['%s|%s|w%.1f' % (key, k, w)] = dict(cagr=float(np.median(cg(M))), base=float(base), d=float(np.median(d)), pw=float(np.mean(d > 0)))
            print(key, k, w, res['%s|%s|w%.1f' % (key, k, w)], flush=True)
    # N0 synthetic
    rng = np.random.default_rng(7); zn = (c.r[:, W:] - c.r[:, W:].mean()) / c.r[:, W:].std(); eps = rng.standard_normal(zn.shape)
    for S in (0.5, 1.0, 1.5):
        for rho in (0.0, 0.3):
            x = rf + S * 0.15 / 252 + 0.15 / np.sqrt(252) * (rho * zn + np.sqrt(1 - rho ** 2) * eps); Es = sleeve_curve(x)
            for w in (0.2, 0.4):
                M = (1 - w) * EE + w * Es; d = cg(M) - cg(EE)
                res['%s|N0 S%.1f rho%.1f|w%.1f' % (key, S, rho, w)] = dict(cagr=float(np.median(cg(M))), base=float(base), d=float(np.median(d)), pw=float(np.mean(d > 0)), alone=float(np.median(cg(Es))))
                print(key, 'N0', S, rho, w, res['%s|N0 S%.1f rho%.1f|w%.1f' % (key, S, rho, w)], flush=True)
json.dump(res, open(RES + '/mix.json', 'w'), indent=1)
