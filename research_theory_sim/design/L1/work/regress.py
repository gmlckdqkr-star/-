import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import sim
from feat import ewma, fwd_sum
np.seterr(all='ignore')
P, T = 1000, 7860
for mech in (True, False):
    s = sim.simulate(P, T, seed=3, mechanism=mech)
    r, rf = s['r'], s['rf']
    lr = np.log1p(r); lp = np.cumsum(lr, 1)
    sig = np.sqrt(252 * ewma(lr ** 2, 20, init=1e-4))
    X = {}
    for n in (10, 21, 63, 126, 252):
        X[f'g{n}'] = (lp - ewma(lp, n)) 
    d = np.exp(-np.log(2) / 252); M = np.empty_like(sig); m = sig[:, 0].copy()
    for t in range(T): m = np.maximum(sig[:, t], m * d); M[:, t] = m
    X['lgap'] = np.log(M / sig)
    X['lsig'] = np.log(sig)
    for H in (21, 63):
        y = fwd_sum(lr - rf, H)[:, 2:] * 252 / H
        sl = slice(400, T - H - 2)
        names = list(X)
        A = np.stack([X[k][:, :T-2][:, sl] for k in names], -1)
        Y = y[:, sl]
        A = A - A.mean(1, keepdims=True); Y = Y - Y.mean(1, keepdims=True)
        A2 = A.reshape(-1, len(names)); Y2 = Y.reshape(-1)
        ok = np.isfinite(A2).all(1) & np.isfinite(Y2)
        A2, Y2 = A2[ok], Y2[ok]
        sd = A2.std(0)
        b = np.linalg.lstsq(A2 / sd, Y2, rcond=None)[0]
        R2 = 1 - np.var(Y2 - (A2 / sd) @ b) / np.var(Y2)
        print(f'mech {mech} H={H} R2={R2:.4f} coef per 1sd (ann ex):', {k: round(float(v), 4) for k, v in zip(names, b)})
        # univariate
        uni = {k: round(float(np.corrcoef(A2[:, i], Y2)[0, 1]), 4) for i, k in enumerate(names)}
        print('    univariate corr', uni)
