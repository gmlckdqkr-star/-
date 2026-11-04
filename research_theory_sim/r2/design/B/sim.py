"""Simulator of the 'two-clock yardstick learning' (TCYL) theory -- lane TS2 round 2, designer B.

simulate(P, T, seed, mechanism=True, prior_scale=1.0) -> dict(r=(P,T), rf=(P,T), y10=(P,T), params=dict of per-path arrays)
(prior_scale is for robustness checks only; the frozen prior is prior_scale = 1)

Every parameter is drawn PER PATH from the priors frozen in THEORY.md (section 8). The same seed gives the same
draws (premium, volatility, shocks, volatility process, rates) with the mechanism ON or OFF; OFF sets the feedback
coefficients A = B = 0 (beliefs do not move the price). In both worlds the shock scale is set per path so that the
realised daily volatility equals the drawn sigma, and the log drift is (rf + mu - sigma^2/2)/252.
Pure numpy, vectorised over paths; the time loop is sequential because the close is a fixed point of the beliefs.
"""
import numpy as np

BURN = 500          # burn-in days before column 0 (removes start-up transients of beliefs and rates)
C_ABS = 1.25        # E|x| -> sigma conversion (sqrt(pi/2))


def _draw_params(g, P):
    p = {}
    mu = g.normal(0.030, 0.025, P)
    for _ in range(50):                                   # truncated normal by redraw
        bad = (mu < -0.03) | (mu > 0.10)
        if not bad.any(): break
        mu[bad] = g.normal(0.030, 0.025, bad.sum())
    p['mu'] = np.clip(mu, -0.03, 0.10)
    sg = np.exp(np.log(0.17) + 0.25 * g.standard_normal(P))
    for _ in range(50):
        bad = (sg < 0.08) | (sg > 0.40)
        if not bad.any(): break
        sg[bad] = np.exp(np.log(0.17) + 0.25 * g.standard_normal(bad.sum()))
    p['sigma'] = np.clip(sg, 0.08, 0.40)
    p['nu'] = g.uniform(4.0, 12.0, P)
    p['h_v'] = np.exp(g.uniform(np.log(20.0), np.log(500.0), P))
    p['s_v'] = g.uniform(0.15, 0.55, P)
    # mechanism (always drawn so that ON and OFF share all other draws)
    A = g.uniform(0.00, 0.45, P)
    B = g.uniform(0.00, 0.40, P)
    tot = A + B
    sc = np.where(tot > 0.70, 0.70 / np.maximum(tot, 1e-12), 1.0)
    p['A'] = A * sc; p['B'] = B * sc
    p['h_m'] = np.exp(g.uniform(np.log(1.5), np.log(12.0), P))          # years
    p['h_s'] = np.exp(g.uniform(np.log(10.0), np.log(150.0), P))        # trading days
    p['rho'] = g.uniform(0.3, 1.0, P)
    # rates
    p['rf0'] = g.uniform(0.0, 0.08, P)
    p['rf_monthly'] = g.uniform(0, 1, P) < 0.4
    p['tp'] = g.uniform(0.005, 0.025, P)
    return p


def _rescale_prior(p, w):
    """robustness only: narrow (w < 1) or widen (w > 1) every market prior around its centre (same base draws).
    w = 1 returns the frozen prior unchanged."""
    if w == 1.0: return p
    lin = lambda v, c, lo, hi: np.clip(c + w * (v - c), lo, hi)
    lg = lambda v, c, lo, hi: np.clip(np.exp(np.log(c) + w * (np.log(v) - np.log(c))), lo, hi)
    p['mu'] = lin(p['mu'], 0.03, -0.20, 0.30)
    p['sigma'] = lg(p['sigma'], 0.17, 0.04, 0.80)
    p['nu'] = lin(p['nu'], 8.0, 3.0, 50.0)
    p['h_v'] = lg(p['h_v'], 100.0, 2.0, 5000.0)
    p['s_v'] = lin(p['s_v'], 0.35, 0.01, 1.0)
    A = lin(p['A'], 0.225, 0.0, 0.95); B = lin(p['B'], 0.20, 0.0, 0.95)
    tot = A + B; sc = np.where(tot > 0.70, 0.70 / np.maximum(tot, 1e-12), 1.0)
    p['A'] = A * sc; p['B'] = B * sc
    p['h_m'] = lg(p['h_m'], np.sqrt(1.5 * 12.0), 0.2, 50.0)
    p['h_s'] = lg(p['h_s'], np.sqrt(10.0 * 150.0), 2.0, 1000.0)
    p['rho'] = lin(p['rho'], 0.65, 0.0, 1.0)
    return p


def _rates(g, p, P, N):
    """annual short rate (P, N) with back-to-back regimes (up / down / flat) of 3-15 years, AR noise, jumps, ZLB."""
    K = int(N / (3 * 252)) + 2
    dur = (g.uniform(3.0, 15.0, (P, K)) * 252).astype(int)
    typ = g.integers(0, 3, (P, K))
    mag = g.uniform(0.002, 0.012, (P, K))
    slope_k = np.where(typ == 0, mag, np.where(typ == 1, -mag, 0.0))     # per year
    # random phase: the path starts somewhere inside its first regime
    start = (g.uniform(0, 1, P) * dur[:, 0]).astype(int)
    bounds = np.cumsum(dur, axis=1) - start[:, None]
    days = np.arange(N)
    slope = np.empty((P, N))
    for i in range(P):
        k = np.searchsorted(bounds[i], days, side='right')
        slope[i] = slope_k[i, np.minimum(k, K - 1)]
    jump = (g.uniform(0, 1, (P, N)) < 0.15 / 252) * np.where(g.uniform(0, 1, (P, N)) < 0.5, -0.01, 0.01)
    phi = 0.5 ** (1 / 126.0)
    e = g.standard_normal((P, N)) * 0.003 * np.sqrt(1 - phi ** 2)
    L = p['rf0'].copy(); n = g.standard_normal(P) * 0.003
    out = np.empty((P, N))
    for t in range(N):
        L = np.clip(L + slope[:, t] / 252 + jump[:, t], 0.0, 0.16)
        n = phi * n + e[:, t]
        out[:, t] = np.clip(L + n * np.minimum(1.0, L / 0.01), 0.0, 0.16)
    m = p['rf_monthly']
    if m.any():
        idx = (days // 21) * 21
        out[m] = out[m][:, idx]
    # y10 (percent): half current rate, half 2-year-ish average, plus term premium and slow noise
    lam = 1 - 0.5 ** (1 / 252.0)
    ew = out[:, 0].copy(); y = np.empty((P, N))
    phy = 0.5 ** (1 / 252.0)
    ey = g.standard_normal((P, N)) * 0.3 * np.sqrt(1 - phy ** 2); ny = np.zeros(P)
    for t in range(N):
        ew = ew + lam * (out[:, t] - ew)
        ny = phy * ny + ey[:, t]
        y[:, t] = np.maximum(100 * (0.5 * out[:, t] + 0.5 * ew + p['tp']) + ny, 0.2)
    if m.any():
        y[m] = y[m][:, idx]
    return out, y


def _solve_on(d, u, c, rfa, p, s0, m0):
    """fixed point of price <- beliefs <- experienced returns, day by day. Returns log returns x (P, N)."""
    P, N = u.shape
    A, B = p['A'], p['B']
    km = 1 - 0.5 ** (1 / (p['h_m'] * 252))          # daily gain of hope
    ks = 1 - 0.5 ** (1 / p['h_s'])                   # daily gain of fear
    a = A / (km * 252)                               # years
    b = B / (ks * C_ABS * np.sqrt(252))
    up = 1.0 / (1 - A + B); dn = 1.0 / (1 - A - B)
    m = m0.copy(); s = s0.copy()
    x = np.empty((P, N))
    for t in range(N):
        drf = rfa[:, t] - rfa[:, t - 1] if t > 0 else 0.0
        z = d[:, t] + c * u[:, t] - a * km * m + b * ks * s - a * p['rho'] * drf
        xt = np.where(z >= 0, z * up, z * dn)
        x[:, t] = xt
        m = m + km * (252 * xt - m)
        s = s + ks * (C_ABS * np.sqrt(252) * np.abs(xt) - s)
    return x


def simulate(P, T, seed, mechanism=True, prior_scale=1.0):
    g = np.random.default_rng(seed)
    N = BURN + T
    p = _draw_params(g, P)
    p = _rescale_prior(p, float(prior_scale))
    rfa, y10 = _rates(g, p, P, N)
    # exogenous log-volatility (unit mean square) and Student-t shocks (unit variance)
    phv = 0.5 ** (1 / p['h_v'])
    hv = np.empty((P, N)); h = g.standard_normal(P) * p['s_v']
    ev = g.standard_normal((P, N))
    for t in range(N):
        h = phv * h + p['s_v'] * np.sqrt(1 - phv ** 2) * ev[:, t]
        hv[:, t] = h
    vol = np.exp(hv - p['s_v'][:, None] ** 2)
    nu = p['nu'][:, None]
    chi = 2.0 * g.standard_gamma(np.broadcast_to(nu / 2, (P, N)))
    eps = g.standard_normal((P, N)) / np.sqrt(chi / nu) * np.sqrt((nu - 2) / nu)
    u = vol * eps
    sig = p['sigma'][:, None]
    d = (rfa + p['mu'][:, None] - sig ** 2 / 2) / 252
    tgt = p['sigma'] / np.sqrt(252)
    m0 = rfa[:, 0] + p['mu'] - p['sigma'] ** 2 / 2 + g.standard_normal(P) * p['sigma'] * 0.3
    s0 = p['sigma'] * np.exp(0.2 * g.standard_normal(P))
    if mechanism:
        c1 = tgt * (1 - p['A'])
        x = _solve_on(d, u, c1, rfa, p, s0, m0)
        r1 = np.std(x[:, BURN:], axis=1)
        c2 = c1 * tgt / r1
        x = _solve_on(d, u, c2, rfa, p, s0, m0)
        p['shock_scale'] = c2
    else:
        c = tgt / np.std(u[:, BURN:], axis=1)          # scale only (shocks are NOT demeaned: sampling noise kept)
        x = d + c[:, None] * u
        p['shock_scale'] = c
    x = x[:, BURN:]
    r = np.expm1(x); r[:, 0] = 0.0
    p['mechanism'] = bool(mechanism)
    return dict(r=r, rf=rfa[:, BURN:] / 252, y10=y10[:, BURN:], params=p)


def describe(sim, label=''):
    """descriptive statistics of a synthetic world (they describe the theory; they are not targets)."""
    import sys
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
    import exec_engine as ee
    r, rf = sim['r'], sim['rf']
    W = ee.WARM
    rr, ff = r[:, W:], rf[:, W:]
    prem = (rr.mean(1) - ff.mean(1)) * 252
    vol = rr.std(1) * np.sqrt(252)
    lp = np.cumsum(np.log1p(rr), axis=1)
    dd = (lp - np.maximum.accumulate(np.maximum(lp, 0), axis=1)).min(1)
    worst = np.expm1(dd)
    lx = np.log1p(rr)
    skew = ((lx - lx.mean(1, keepdims=True)) ** 3).mean(1) / lx.std(1) ** 3
    h1 = ee.hold(r, rf, 1)
    q = lambda a: '%.3f [%.3f, %.3f]' % (np.median(a), np.percentile(a, 10), np.percentile(a, 90))
    print('%s P=%d  median [p10, p90]' % (label, r.shape[0]))
    print('  premium (arith, ann.)   ', q(prem))
    print('  volatility (ann.)       ', q(vol))
    print('  worst drawdown (index)  ', q(worst), ' P(worst<=-50%%)=%.2f  P(<=-80%%)=%.2f' % (np.mean(worst <= -0.5), np.mean(worst <= -0.8)))
    print('  daily skew (log)        ', q(skew))
    print('  rf mean (ann.)          ', q(ff.mean(1) * 252))
    print('  hold 1x CAGR (after tax)', q(h1['cagr']))
    return dict(prem_med=float(np.median(prem)), vol_med=float(np.median(vol)), worst_dd_med=float(np.median(worst)),
                hold1_cagr_med=float(np.median(h1['cagr'])))


if __name__ == '__main__':
    import time
    T = 300 + 30 * 252
    for mech in (True, False):
        t0 = time.time()
        s = simulate(2000, T, 1, mechanism=mech)
        print('simulate(2000, %d) mechanism=%s: %.1fs' % (T, mech, time.time() - t0))
        describe(s, 'ON ' if mech else 'OFF')
