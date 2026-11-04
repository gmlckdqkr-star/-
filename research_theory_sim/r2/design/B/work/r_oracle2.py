"""ceiling check (NOT a candidate): timing with the TRUE conditional drift and variance of the ON world.
Re-solves the ON fixed point with the same draws and records K_t and the true shock scale."""
import sys, numpy as np
from lib import *
import sim as S
P = 500; seed = 11
def solve_diag(P, T, seed):
    g = np.random.default_rng(seed); N = S.BURN + T
    p = S._draw_params(g, P); rfa, y10 = S._rates(g, p, P, N)
    phv = 0.5 ** (1 / p['h_v']); hv = np.empty((P, N)); h = g.standard_normal(P) * p['s_v']; ev = g.standard_normal((P, N))
    for t in range(N):
        h = phv * h + p['s_v'] * np.sqrt(1 - phv ** 2) * ev[:, t]; hv[:, t] = h
    vol = np.exp(hv - p['s_v'][:, None] ** 2); nu = p['nu'][:, None]
    chi = 2.0 * g.standard_gamma(np.broadcast_to(nu / 2, (P, N)))
    eps = g.standard_normal((P, N)) / np.sqrt(chi / nu) * np.sqrt((nu - 2) / nu); u = vol * eps
    sig = p['sigma'][:, None]; d = (rfa + p['mu'][:, None] - sig ** 2 / 2) / 252; tgt = p['sigma'] / np.sqrt(252)
    m0 = rfa[:, 0] + p['mu'] - p['sigma'] ** 2 / 2 + g.standard_normal(P) * p['sigma'] * 0.3
    s0 = p['sigma'] * np.exp(0.2 * g.standard_normal(P))
    c1 = tgt * (1 - p['A']); x = S._solve_on(d, u, c1, rfa, p, s0, m0); c2 = c1 * tgt / np.std(x[:, S.BURN:], axis=1)
    A, B = p['A'], p['B']; km = 1 - 0.5 ** (1 / (p['h_m'] * 252)); ks = 1 - 0.5 ** (1 / p['h_s'])
    a = A / (km * 252); b = B / (ks * S.C_ABS * np.sqrt(252)); up = 1 / (1 - A + B); dn = 1 / (1 - A - B)
    m = m0.copy(); s = s0.copy(); X = np.empty((P, N)); EX = np.empty((P, N)); SD = np.empty((P, N))
    zz = g.standard_normal(4000)  # MC for expectation of piecewise map under normal approx
    for t in range(N):
        drf = rfa[:, t] - rfa[:, t - 1] if t > 0 else 0.0
        K = d[:, t] - a * km * m + b * ks * s
        sc = c2 * vol[:, t]
        # E[x] under z ~ K + sc*N(0,1)
        zs = K[:, None] + sc[:, None] * zz[None, :400]
        xs = np.where(zs >= 0, zs * up[:, None], zs * dn[:, None])
        EX[:, t] = xs.mean(1); SD[:, t] = xs.std(1)
        z = K + c2 * u[:, t] - a * p['rho'] * drf
        xt = np.where(z >= 0, z * up, z * dn); X[:, t] = xt
        m = m + km * (252 * xt - m); s = s + ks * (S.C_ABS * np.sqrt(252) * np.abs(xt) - s)
    X = X[:, S.BURN:]; EX = EX[:, S.BURN:]; SD = SD[:, S.BURN:]
    r = np.expm1(X); r[:, 0] = 0
    return dict(r=r, rf=rfa[:, S.BURN:] / 252, EX=EX, SD=SD, params=p)
D = solve_diag(P, T, seed)
mu_ar = (D['EX'] + D['SD'] ** 2 / 2 - D['rf']) * 252; var = (D['SD'] ** 2) * 252
print('true cond. arith excess (ann.) quantiles', np.percentile(mu_ar[:, 300:], [5, 25, 50, 75, 95]))
for k in (0.25, 0.5, 1.0):
    Bk = np.clip(k * mu_ar / var, 0, 3)
    print('timing-oracle k', k, score(Bk, D), 'hold1', ee.summary(ee.hold(D['r'], D['rf'], 1))['cagr_med'])
