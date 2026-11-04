import numpy as np, json
from spa_mine import spa
z = np.load('../m2/results/grid_disc_X.npz'); X = z['X'].astype(np.float64); n, m = X.shape
dbar = X.mean(0)
B, pblk, rng = 1000, 1.0/3.0, np.random.default_rng(20261104)          # worker's exact bootstrap draws
Cnt = np.zeros((B, n))
for b in range(B):
    idx = np.empty(n, np.int64); idx[0] = rng.integers(n)
    for t in range(1, n):
        idx[t] = rng.integers(n) if rng.random() < pblk else (idx[t-1] + 1) % n
    Cnt[b] = np.bincount(idx, minlength=n)
Dstar = Cnt @ X / n
omega = np.maximum(np.sqrt(n) * Dstar.std(0, ddof=1), 1e-12)
tstat = np.sqrt(n) * dbar / omega; T = max(0, tstat.max())
thr = -np.sqrt(2*np.log(np.log(n)))
# worker formulas (as written in mtest.py)
mu_c_w = np.where(tstat >= thr, dbar, 0.0)
w_c = np.maximum(0, (np.sqrt(n)*(Dstar - dbar + mu_c_w)/omega).max(1))
w_u = np.maximum(0, (np.sqrt(n)*(Dstar - dbar + dbar)/omega).max(1))
w_l = np.maximum(0, (np.sqrt(n)*(Dstar - dbar + np.maximum(dbar, 0))/omega).max(1))
print('worker formulas: T=%.3f p_c=%.3f p_u=%.3f p_l=%.3f' % (T, (w_c >= T).mean(), (w_u >= T).mean(), (w_l >= T).mean()))
# Hansen (2005): Z* = dbar* - g(dbar);  g_u = dbar, g_c = dbar*1{dbar >= -se*sqrt(2loglog n)}, g_l = max(dbar,0)
g_c = np.where(tstat >= thr, dbar, 0.0); g_u = dbar; g_l = np.maximum(dbar, 0)
f = lambda g: np.maximum(0, (np.sqrt(n)*(Dstar - g)/omega).max(1))
c_c, c_u, c_l = f(g_c), f(g_u), f(g_l)
print('corrected Hansen: p_c=%.3f p_u=%.3f p_l=%.3f  null max-t q50 %.2f q95 %.2f' % ((c_c >= T).mean(), (c_u >= T).mean(), (c_l >= T).mean(), np.median(c_u), np.quantile(c_u, .95)))
res, t, Tu = spa(X.T.astype(np.float32).copy(), seed=11)
print('verifier independent SPA (different draws):', res)
# rules with positive mean: how much the inverted centering shifted them
print('share of variants with dbar >= thr*se (recentred wrongly):', float((tstat >= thr).mean()))
