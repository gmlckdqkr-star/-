"""sim.py - synthetic markets for the theory "Fast Aftershocks, Slow Scars" (FASS), lane TS2 r2, designer C.

simulate(P, T, seed, mechanism=True, prior_scale=1.0) -> dict(r=(P,T), rf=(P,T), y10=(P,T), params=dict of (P,) arrays)
  r  : simple daily return of a price index (r[:, 0] = 0)
  rf : simple daily risk-free rate
  y10: 10-year yield in percent (generated, not used by my rule)
All parameters are drawn PER PATH from the priors frozen in THEORY.md section 7. Pure numpy, no data.
Paths are simulated in fixed chunks of 250 so that path i depends only on (seed, i // 250).
Run `python sim.py` to print descriptive statistics of the ON and OFF worlds.
"""
import numpy as np

DPY = 252
BURN = 756          # internal burn-in days, discarded
CHUNK = 250
MCAP = 1.5          # cap on |state-dependent part of m(t)| per year


def _scaled_u(g, a, b, n, s, lo=-np.inf, hi=np.inf):
    c = 0.5 * (a + b)
    return np.clip(g.uniform(c - s * (c - a), c + s * (b - c), n), lo, hi)


def _trunc_normal(g, mu, sd, a, b, n):
    out = g.normal(mu, sd, n)
    bad = (out < a) | (out > b)
    while bad.any():
        out[bad] = g.normal(mu, sd, bad.sum())
        bad = (out < a) | (out > b)
    return out


def draw_params(g, n, s=1.0):
    p = {}
    # market level (anchors) ------------------------------------------------------------------
    a, b = 0.030 - s * 0.050, 0.030 + s * 0.060
    p['pi_bar'] = _trunc_normal(g, 0.030, 0.020 * s, max(a, -0.04), min(b, 0.12), n)
    la, lb = np.log(0.10 / 0.175) * s, np.log(0.35 / 0.175) * s
    ls = _trunc_normal(g, 0.0, 0.25 * s, la, lb, n)
    p['sigma_bar'] = np.clip(0.175 * np.exp(ls), 0.07, 0.45)
    # crash process ---------------------------------------------------------------------------
    p['jshare'] = _scaled_u(g, 0.10, 0.35, n, s, 0.02, 0.6)
    p['Ybar'] = _scaled_u(g, 0.025, 0.055, n, s, 0.01, 0.10)
    p['kY'] = _scaled_u(g, 1.5, 4.0, n, s, 0.8, 8.0)
    p['n'] = _scaled_u(g, 0.30, 0.80, n, s, 0.0, 0.9)
    p['tau1'] = _scaled_u(g, 5, 30, n, s, 2, 60)
    p['tau2'] = _scaled_u(g, 40, 160, n, s, 20, 300)
    p['w1'] = _scaled_u(g, 0.3, 0.8, n, s, 0.05, 0.95)
    p['tau_b'] = _scaled_u(g, 1.0, 6.0, n, s, 0.3, 10.0)
    p['s_b'] = _scaled_u(g, 0.2, 0.9, n, s, 0.0, 1.5)
    p['xi'] = _scaled_u(g, 0.0, 0.5, n, s, 0.0, 1.0)
    p['zeta'] = _scaled_u(g, 0.3, 1.0, n, s, 0.0, 1.5)
    # beliefs and pricing ---------------------------------------------------------------------
    p['theta_a'] = _scaled_u(g, 0.2, 1.0, n, s, 0.0, 1.0)
    p['theta_b'] = _scaled_u(g, 0.0, 1.0, n, s, 0.0, 1.0)
    p['theta_s'] = _scaled_u(g, 0.0, 0.6, n, s, 0.0, 1.0)
    p['tau_s'] = _scaled_u(g, 0.5, 3.0, n, s, 0.1, 6.0)
    p['psi'] = _scaled_u(g, 0.0, 2.0, n, s, 0.0, 4.0)
    p['q'] = _scaled_u(g, 0.0, 0.5, n, s, 0.0, 0.7)
    p['tau_r'] = _scaled_u(g, 0.25, 1.5, n, s, 0.05, 3.0)
    # derived
    EY2 = p['Ybar'] ** 2 * (1 + 1 / p['kY'])
    p['lam_bar'] = p['jshare'] * p['sigma_bar'] ** 2 / EY2
    return p


def _rates(g, n, Ttot):
    """rf (annual) and y10 (percent) paths with long trend/stable regimes (brief 2d). Prior: THEORY.md section 7."""
    lvl = g.uniform(0.0, 0.08, n)
    slope = np.zeros(n); left = np.zeros(n, dtype=np.int64)
    noise = np.zeros(n); a_n = np.exp(-1 / (0.5 * DPY)); sd_n = 0.004
    sp_m = g.uniform(0.005, 0.02, n); sp_tau = g.uniform(1.0, 3.0, n)
    a_sp = np.exp(-1 / (sp_tau * DPY)); sp = sp_m + 0.01 * g.normal(size=n)
    monthly = g.uniform(size=n) < 0.5
    RF = np.empty((n, Ttot)); Y10 = np.empty((n, Ttot))
    for t in range(Ttot):
        new = left <= 0
        if new.any():
            k = new.sum()
            left[new] = (g.uniform(4, 15, k) * DPY).astype(np.int64)
            typ = g.integers(0, 3, k)                       # 0 up, 1 down, 2 stable
            sl = g.uniform(0.002, 0.008, k)
            slope[new] = np.where(typ == 0, sl, np.where(typ == 1, -sl, 0.0))
        lvl = lvl + slope / DPY
        hit = (lvl < 0) | (lvl > 0.15)
        if hit.any():
            lvl = np.where(lvl < 0, -lvl, lvl); lvl = np.where(lvl > 0.15, 0.30 - lvl, lvl)
            slope = np.where(hit, 0.0, slope)
        left -= 1
        noise = a_n * noise + np.sqrt(1 - a_n ** 2) * sd_n * g.normal(size=n)
        sp = a_sp * sp + (1 - a_sp) * sp_m + np.sqrt(1 - a_sp ** 2) * 0.01 * g.normal(size=n)
        RF[:, t] = np.clip(lvl + noise, 0.0, 0.16)
        Y10[:, t] = np.maximum(100 * (RF[:, t] + sp), 0.1)
    if monthly.any():
        idx = (np.arange(Ttot) // 21) * 21
        RF[monthly] = RF[monthly][:, idx]; Y10[monthly] = Y10[monthly][:, idx]
    return RF, Y10, monthly


def _chunk(seed, ci, n, T, mechanism, s, diag, override=None):
    gp = np.random.default_rng([seed, ci, 1])      # parameters
    gr = np.random.default_rng([seed, ci, 2])      # rates
    gx = np.random.default_rng([seed, ci, 3])      # returns (mechanism-specific stream)
    p = draw_params(gp, n, s)
    if override:                                   # diagnostics only (attribution); never used for the priors
        for k, v in override.items(): p[k] = np.full(n, float(v))
        p['lam_bar'] = p['jshare'] * p['sigma_bar'] ** 2 / (p['Ybar'] ** 2 * (1 + 1 / p['kY']))
    Ttot = T + BURN
    RF, Y10, monthly = _rates(gr, n, Ttot)
    sb2 = p['sigma_bar'] ** 2
    base = p['pi_bar'] - 0.5 * sb2                 # log excess drift (annual)
    sD = np.sqrt((1 - p['jshare']) * sb2)
    lam_bar = p['lam_bar']; Ybar = p['Ybar']; kY = p['kY']
    if not mechanism:
        pbar = 1 - np.exp(-lam_bar / DPY)
        N = gx.uniform(size=(n, T)) < pbar[:, None]
        Y = gx.gamma(kY[:, None], (Ybar / kY)[:, None], size=(n, T))
        x = (base / DPY + pbar * Ybar)[:, None] + sD[:, None] * gx.normal(size=(n, T)) / np.sqrt(DPY) - Y * N
        extra = None
    else:
        nn = p['n']; lam_bb = lam_bar * (1 - nn)
        e1 = np.exp(-1 / p['tau1']); e2 = np.exp(-1 / p['tau2'])
        j1 = nn * p['w1'] * DPY / p['tau1']; j2 = nn * (1 - p['w1']) * DPY / p['tau2']
        a_b = np.exp(-1 / (p['tau_b'] * DPY)); s_b = p['s_b']
        e_s = np.exp(-1 / (p['tau_s'] * DPY)); j_s = p['theta_s'] / p['tau_s']
        e_r = np.exp(-1 / (p['tau_r'] * DPY))
        xi = p['xi']; ynorm = np.exp(xi * s_b ** 2 * (2 * xi - 1) / 2)
        th_a, th_b, psi, q = p['theta_a'], p['theta_b'], p['psi'], p['q']
        Hbar = nn * lam_bar; Sbar = p['theta_s'] * lam_bar
        u = s_b * gx.normal(size=n)
        H1 = np.full(n, Hbar * p['w1']); H2 = np.full(n, Hbar * (1 - p['w1']))
        S = Sbar.copy(); dl = np.zeros(n)
        dev = np.empty((n, T), dtype=np.float32); vz = np.empty((n, T), dtype=np.float32)
        jt = np.empty((n, T)); NN = np.zeros((n, T), dtype=bool) if diag else None
        LAM = np.empty((n, T), dtype=np.float32) if diag else None
        for t in range(Ttot):
            lam_b = lam_bb * np.exp(u - 0.5 * s_b ** 2)
            H = H1 + H2
            lam = lam_b + H
            pt = 1 - np.exp(-lam / DPY)
            Yb = Ybar * np.exp(xi * (u - 0.5 * s_b ** 2)) / ynorm
            N = gx.uniform(size=n) < pt
            Y = gx.gamma(kY, Yb / kY) * N
            if t >= BURN:
                k = t - BURN
                lam_tilde_dev = th_a * (H - Hbar) + th_b * (lam_b - lam_bb) + (S - Sbar)
                d = Yb * ((1 + psi) * lam_tilde_dev - (lam - lam_bar)) + dl / p['tau_r']
                dev[:, k] = np.clip(d, -MCAP, MCAP)
                vz[:, k] = (lam / lam_bar) ** p['zeta']
                jt[:, k] = pt * Yb - Y
                if diag: NN[:, k] = N; LAM[:, k] = lam
            # state updates with today's crash
            H1 = H1 * e1 + j1 * N; H2 = H2 * e2 + j2 * N
            S = S * e_s + j_s * N
            dl = dl * e_r + q * Y
            u = a_b * u + np.sqrt(1 - a_b ** 2) * s_b * gx.normal(size=n)
        dev = dev.astype(np.float64); dev -= dev.mean(axis=1, keepdims=True)
        vz = vz.astype(np.float64); vz /= vz.mean(axis=1, keepdims=True)
        x = (base[:, None] + dev) / DPY + jt + sD[:, None] * np.sqrt(vz) * gx.normal(size=(n, T)) / np.sqrt(DPY)
        extra = dict(m=base[:, None] + dev, var_d=sD[:, None] ** 2 * vz, N=NN, lam=LAM) if diag else None
        del dev, vz, jt
    rf = RF[:, BURN:] / DPY
    r = np.expm1(x + np.log1p(rf))
    r[:, 0] = 0.0
    p['monthly_rates'] = monthly
    return r, rf, Y10[:, BURN:], p, extra


def simulate(P, T, seed, mechanism=True, prior_scale=1.0, diag=False, override=None):
    rs, fs, ys, ps, ex = [], [], [], [], []
    nch = (P + CHUNK - 1) // CHUNK
    for ci in range(nch):
        n = min(CHUNK, P - ci * CHUNK)
        r, rf, y10, p, e = _chunk(seed, ci, CHUNK, T, mechanism, prior_scale, diag, override)
        rs.append(r[:n]); fs.append(rf[:n]); ys.append(y10[:n]); ps.append({k: v[:n] for k, v in p.items()})
        if diag: ex.append({k: (v[:n] if v is not None else None) for k, v in e.items()} if e else None)
    out = dict(r=np.concatenate(rs), rf=np.concatenate(fs), y10=np.concatenate(ys),
               params={k: np.concatenate([q[k] for q in ps]) for k in ps[0]})
    if diag and ex[0] is not None:
        out['diag'] = {k: (np.concatenate([e[k] for e in ex]) if ex[0][k] is not None else None) for k in ex[0]}
    return out


def describe(sim, label=''):
    import sys
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
    import exec_engine as ee
    r, rf = sim['r'], sim['rf']; W = ee.WARM
    rr, ff = r[:, W:], rf[:, W:]
    prem = (rr - ff).mean(axis=1) * DPY
    vol = rr.std(axis=1) * np.sqrt(DPY)
    lp = np.cumsum(np.log1p(rr), axis=1)
    mdd = (lp - np.maximum.accumulate(np.maximum(lp, 0), axis=1)).min(axis=1)
    mdd = np.expm1(mdd)
    z = (rr - rr.mean(axis=1, keepdims=True)) / rr.std(axis=1, keepdims=True)
    big = z < -3
    # clustering: P(big day within next 20 days | big day today) vs unconditional
    nxt = np.zeros_like(big)
    for k in range(1, 21): nxt[:, :-k] |= big[:, k:]
    cond = (nxt & big).sum() / max(big.sum(), 1); unc = nxt.mean()
    # |r| autocorrelation at lag 1..20 (avg)
    a = np.abs(rr) - np.abs(rr).mean(axis=1, keepdims=True)
    ac = np.mean([np.mean((a[:, k:] * a[:, :-k]).mean(axis=1) / a.var(axis=1)) for k in (1, 5, 20)])
    m21 = np.add.reduceat(np.log1p(rr), np.arange(0, rr.shape[1], 21), axis=1)
    sk = np.median(((m21 - m21.mean(1, keepdims=True)) ** 3).mean(1) / m21.std(1) ** 3)
    h1 = ee.hold(r, rf, 1)['cagr']
    q = lambda v: '%.4f [%.4f, %.4f]' % (np.median(v), np.percentile(v, 10), np.percentile(v, 90))
    print(f'--- {label}  P={r.shape[0]} T={r.shape[1]}')
    print('  realised arith excess premium/yr  med [p10,p90]:', q(prem))
    print('  realised vol/yr                   :', q(vol))
    print('  worst drawdown (price index)      :', q(mdd), ' P(mdd<=-50%%)=%.3f  P(mdd<=-40%%)=%.3f' % (np.mean(mdd <= -0.5), np.mean(mdd <= -0.4)))
    print('  hold 1x after-tax CAGR            :', q(h1))
    print('  P(z<-3 day in next 20 | z<-3 today)=%.3f vs uncond %.3f ; mean |r| autocorr (lags 1,5,20)=%.3f ; median monthly skew=%.2f'
          % (cond, unc, ac, sk))
    return dict(prem=prem, vol=vol, mdd=mdd, h1=h1)


if __name__ == '__main__':
    import time
    T = 300 + 30 * 252
    for mech in (True, False):
        t0 = time.time()
        s = simulate(2000, T, seed=1, mechanism=mech)
        print('sim time %.1fs' % (time.time() - t0))
        describe(s, 'mechanism ON' if mech else 'mechanism OFF')
        pr = s['params']
        print('  per-path drawn pi_bar med %.4f, sigma_bar med %.4f, lam_bar med %.2f/yr [%.2f, %.2f]' % (
            np.median(pr['pi_bar']), np.median(pr['sigma_bar']), np.median(pr['lam_bar']),
            np.percentile(pr['lam_bar'], 10), np.percentile(pr['lam_bar'], 90)))
        print('  rf/yr: median %.4f, p10 %.4f, p90 %.4f ; y10 median %.2f%%' % (
            np.median(s['rf']) * DPY, np.percentile(s['rf'], 10) * DPY, np.percentile(s['rf'], 90) * DPY, np.median(s['y10'])))
