"""Simulator of the Funding-Carry Capital Ledger (FCCL) theory - lane TS2 round 2, designer D.

simulate(P, T, seed, mechanism=True) -> dict(r=(P,T), rf=(P,T), y10=(P,T), params=dict of (P,) arrays)
  r   : simple daily return of the equity price index, r[:, 0] = 0
  rf  : daily short rate (simple, per day)
  y10 : 10-year yield in percent
Every parameter is drawn PER PATH from the priors frozen in THEORY.md (section 6).
mechanism=False gives the mechanism-off world: same mu_bar, sigma_bar, df, shocks and rates; i.i.d. returns.
Optional (robustness only): prior_scale (0.5 narrows / 1.5 widens every prior around its centre),
block=True builds each path from 250-day blocks of a longer synthetic history (mimics the headline resampling).
Pure numpy; paths are simulated in chunks of 250 with independent spawned streams (first paths do not depend on P).
No market data of any kind is used.
"""
import numpy as np

DT = 1.0 / 252
CH = 250


def _u(g, n, a, b, s=1.0):
    c, h = 0.5 * (a + b), 0.5 * (b - a) * s
    return g.uniform(c - h, c + h, n)


def draw_params(g, n, prior_scale=1.0):
    s = float(prior_scale)
    p = {}
    p['I_TR'] = (g.random(n) < 0.35).astype(float)
    p['mu_bar'] = np.clip(0.025 + 0.035 * p['I_TR'] + 0.018 * s * g.standard_normal(n), -0.02, 0.10)
    p['sigma_bar'] = np.clip(np.exp(np.log(0.17) + 0.25 * s * g.standard_normal(n)), 0.09, 0.40)
    p['df'] = np.maximum(_u(g, n, 3.5, 8.0, s), 3.0)
    # rates
    p['R0'] = np.maximum(_u(g, n, 0.005, 0.09, s), 0.0)
    p['cyc_hl'] = np.maximum(_u(g, n, 0.5, 2.0, s), 0.1)
    p['cyc_sd'] = np.maximum(_u(g, n, 0.002, 0.012, s), 0.0)
    p['M_hl'] = np.maximum(_u(g, n, 2.0, 6.0, s), 0.5)
    p['omega'] = np.clip(_u(g, n, 0.2, 0.5, s), 0.0, 1.0)
    p['tpbar'] = _u(g, n, 0.003, 0.020, s)
    p['tp_sd'] = np.maximum(_u(g, n, 0.003, 0.010, s), 0.0)
    p['tp_hl'] = np.maximum(_u(g, n, 0.5, 3.0, s), 0.1)
    p['phase'] = g.integers(0, 21, n).astype(float)
    # mechanism
    p['HL_x'] = np.clip(np.exp(np.log(2.0) + 0.4 * s * g.standard_normal(n)), 0.7, 6.0)
    p['m'] = np.maximum(_u(g, n, 1.0, 3.0, s), 0.0)
    p['c'] = np.maximum(_u(g, n, 2.0, 8.0, s), 0.0)
    p['D_y'] = np.maximum(_u(g, n, 0.0, 6.0, s), 0.0)
    p['nu_x'] = np.maximum(_u(g, n, 0.0, 0.15, s), 0.0)
    p['g'] = np.maximum(_u(g, n, 0.2, 1.2, s), 0.0)
    p['rho'] = np.clip(_u(g, n, 0.2, 0.7, s), 0.0, 0.95)
    p['HL_v'] = np.maximum(_u(g, n, 5.0, 40.0, s), 1.0)
    p['b'] = np.maximum(_u(g, n, 0.0, 1.5, s), 0.0)
    p['beta'] = np.clip(_u(g, n, 0.0, 2.0, s), 0.0, 3.0)
    p['phi'] = np.maximum(_u(g, n, 0.05, 0.25, s), 0.0)
    p['x0z'] = g.standard_normal(n)
    return p


def _rates(g, p, T, s=1.0):
    n = p['R0'].size
    tr = p['R0'].copy()
    reg = g.integers(0, 3, n)                       # 0 up, 1 down, 2 stable

    def new_dur(k):
        return np.clip(np.exp(np.log(5.0) + 0.6 * s * g.standard_normal(k)), 1.0, 20.0) * 252

    def new_slope(rg):
        k = rg.size
        mag = np.maximum(_u(g, k, 0.002, 0.009, s), 0.0)
        return np.where(rg == 0, mag, np.where(rg == 1, -mag, 0.0005 * s * g.standard_normal(k)))

    rem = new_dur(n); slope = new_slope(reg)
    a_c = np.exp(-np.log(2) / (p['cyc_hl'] * 252)); cyc = p['cyc_sd'] * g.standard_normal(n)
    a_tp = np.exp(-np.log(2) / (p['tp_hl'] * 252)); tp = p['tpbar'] + p['tp_sd'] * g.standard_normal(n)
    l_M = np.exp(-np.log(2) / (p['M_hl'] * 252))
    R = np.clip(np.round(np.maximum(tr + cyc, 0) / 0.0025) * 0.0025, 0, 0.2); M = R.copy()
    om = p['omega']; ph = p['phase'].astype(int)
    rf = np.empty((n, T)); y10 = np.empty((n, T))
    for t in range(T):
        rem -= 1
        sw = rem <= 0
        sw |= (reg == 1) & (tr <= 0.0)
        sw |= (reg == 0) & (tr >= 0.15)
        if sw.any():
            u = g.random(n)
            nr = (reg + 1 + (u < 0.5)) % 3
            nr = np.where((reg == 1) & (tr <= 0.0), 2, nr)        # zero bound -> stable
            nr = np.where((reg == 0) & (tr >= 0.15), 1, nr)       # ceiling -> down
            reg = np.where(sw, nr, reg)
            rem = np.where(sw, new_dur(n), rem)
            slope = np.where(sw, new_slope(reg), slope)
        tr = np.clip(tr + slope * DT, 0.0, 0.15)
        cyc = a_c * cyc + p['cyc_sd'] * np.sqrt(1 - a_c ** 2) * g.standard_normal(n)
        rstar = np.maximum(tr + cyc, 0.0)
        meet = ((t + ph) % 21) == 0
        stp = np.clip(0.0025 * np.round((rstar - R) / 0.0025), -0.0075, 0.0075)
        R = np.where(meet, np.maximum(R + stp, 0.0), R)
        M = l_M * M + (1 - l_M) * R
        tp = p['tpbar'] + a_tp * (tp - p['tpbar']) + p['tp_sd'] * np.sqrt(1 - a_tp ** 2) * g.standard_normal(n)
        rf[:, t] = R / 252.0
        y10[:, t] = 100.0 * np.maximum(om * R + (1 - om) * M + tp, -0.005)
    return rf, y10


def _states(p, z, eta, S, dY):
    """single pass of the ledger / VaR-loop recursion at the path's normal volatility scale.
    returns A_t (volatility factor, sigma_t = sigma_bar * A_t / K_s) and X_t = x_{t-1} (capital state before day t)."""
    n, T = z.shape
    sb = p['sigma_bar']; kap = np.log(2) / p['HL_x']
    lv = np.exp(-np.log(2) / p['HL_v'])
    x = np.clip(p['x0z'] * p['m'] * sb / np.sqrt(2 * kap), -2, 2)
    w = np.ones(n)
    A = np.ones((n, T)); X = np.zeros((n, T))
    sq = np.sqrt(DT)
    for t in range(1, T):
        a = np.clip(np.exp(-p['g'] * x) * w ** (p['rho'] / 2), 0.25, 6.0)
        A[:, t] = a; X[:, t] = x
        er = sb * a * sq * z[:, t]                       # equity shock at the normal scale
        x = (1 - kap * DT) * x + p['m'] * er + p['c'] * (S[:, t - 1] - p['tpbar']) * DT - p['D_y'] * dY[:, t] \
            + p['nu_x'] * sq * eta[:, t]
        x = np.clip(x, -3.0, 3.0)
        w = lv * w + (1 - lv) * (a * z[:, t]) ** 2
    A[:, 0] = A[:, 1]; X[:, 0] = X[:, 1]
    return A, X


def _chunk(g, n, T, mechanism, prior_scale, states=False):
    p = draw_params(g, n, prior_scale)
    rf, y10 = _rates(g, p, T, prior_scale)
    df = p['df'][:, None]
    z = g.standard_t(np.repeat(df, T, axis=1)) / np.sqrt(df / (df - 2))
    eta = g.standard_normal((n, T))
    z[:, 0] = 0.0; eta[:, 0] = 0.0
    sb = p['sigma_bar'][:, None]; mb = p['mu_bar'][:, None]
    if not mechanism:
        r = np.maximum(rf + mb * DT + sb * np.sqrt(DT) * z, -0.30)
        r[:, 0] = 0.0
        if states:
            p['_sig'] = np.repeat(sb, T, axis=1); p['_mu'] = np.repeat(mb, T, axis=1)
        return r, rf, y10, p
    S = y10 / 100.0 - rf * 252.0
    dY = np.zeros_like(y10); dY[:, 1:] = np.diff(y10, axis=1) / 100.0
    # normalisers from an independent pilot run (same parameters and rates, fresh shocks): using the path's own
    # realised moments would leak the path's future shocks into its scale (a look-ahead bias of the drift).
    NP = 3                                                            # pilot length = 3 x T (rates path tiled)
    zp = g.standard_t(np.repeat(df, NP * T, axis=1)) / np.sqrt(df / (df - 2)); zp[:, 0] = 0.0
    Ap, Xp = _states(p, zp, g.standard_normal((n, NP * T)), np.tile(S, NP), np.tile(dY, NP))
    sgp = np.clip(Ap / np.sqrt(np.mean(Ap[:, 1:] ** 2, axis=1))[:, None], 0.3, 5.0)
    Ks = np.sqrt(np.mean(Ap[:, 1:] ** 2, axis=1)) / np.sqrt(np.mean(sgp[:, 1:] ** 2, axis=1))
    sgp = np.clip(Ap / Ks[:, None], 0.3, 5.0)
    Kq = np.mean(np.clip(np.exp(-p['b'][:, None] * Xp[:, 1:]) * sgp[:, 1:] ** p['beta'][:, None], 0.1, 10.0), axis=1)
    del sgp
    del zp, Ap, Xp
    A, X = _states(p, z, eta, S, dY)
    sig = np.clip(sb * A / Ks[:, None], 0.3 * sb, 5.0 * sb)          # THEORY clip: sigma_t in [0.3, 5] x sigma_bar
    Q = np.clip(np.exp(-p['b'][:, None] * X) * (sig / sb) ** p['beta'][:, None], 0.1, 10.0)   # premium factor clip
    p['K_s'] = Ks; p['K_q'] = Kq
    Sl = np.zeros_like(S); Sl[:, 1:] = S[:, :-1]
    tpb = p['tpbar'][:, None]; phi = p['phi'][:, None]; c = p['c'][:, None]
    mu = mb / Kq[:, None] * Q + phi * c * (Sl - tpb)
    e = sig * np.sqrt(DT) * z
    r = rf + mu * DT + e - phi * p['D_y'][:, None] * dY + phi * p['nu_x'][:, None] * np.sqrt(DT) * eta
    r = np.maximum(r, -0.30)                                          # numerical floor on a daily index return
    r[:, 0] = 0.0
    if states:                                                        # design diagnostics only (oracle)
        p['_sig'] = sig; p['_mu'] = mu; p['_x'] = X
    return r, rf, y10, p


def simulate(P, T, seed, mechanism=True, prior_scale=1.0, block=False, hist_years=60, block_len=250, states=False):
    ss = np.random.SeedSequence([int(seed), 7349])
    nch = (P + CH - 1) // CH
    kids = ss.spawn(nch)
    R, F, Y, PR = [], [], [], []
    for i in range(nch):
        g = np.random.default_rng(kids[i])
        n = min(CH, P - i * CH)
        if not block:
            r, rf, y10, p = _chunk(g, n, T, mechanism, prior_scale, states)
        else:
            H = int(hist_years * 252)
            rh, fh, yh, p = _chunk(g, n, H, mechanism, prior_scale)
            nb = (T + block_len - 1) // block_len
            gb = np.random.default_rng([int(seed), 991, i])           # same blocks ON and OFF
            st = gb.integers(0, H - block_len, (n, nb))
            idx = (st[:, :, None] + np.arange(block_len)[None, None, :]).reshape(n, -1)[:, :T]
            rr = np.arange(n)[:, None]
            r, rf, y10 = rh[rr, idx], fh[rr, idx], yh[rr, idx]
            r[:, 0] = 0.0
        R.append(r); F.append(rf); Y.append(y10); PR.append(p)
    params = {k: np.concatenate([q[k] for q in PR]) for k in PR[0]}
    return dict(r=np.concatenate(R), rf=np.concatenate(F), y10=np.concatenate(Y), params=params)


def describe(d, label=''):
    """descriptive statistics of a synthetic world (they describe the theory; they are not targets)."""
    import sys
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
    import exec_engine as ee
    W = ee.WARM
    r, rf, y = d['r'][:, W:], d['rf'][:, W:], d['y10'][:, W:]
    prem = (r - rf).mean(axis=1) * 252
    vol = r.std(axis=1) * np.sqrt(252)
    lp = np.cumsum(np.log1p(r), axis=1)
    mdd = (lp - np.maximum.accumulate(np.maximum(lp, 0.0), axis=1)).min(axis=1)
    mdd = np.expm1(mdd)
    h1 = ee.hold(d['r'], d['rf'], 1)['cagr']
    yr = r.shape[1] // 252
    ra = np.exp(lp[:, 251::252][:, :yr] - np.concatenate([np.zeros((r.shape[0], 1)), lp[:, 251::252][:, :yr - 1]], 1)) - 1
    vy = np.array([np.std(np.log1p(r[:, k * 252:(k + 1) * 252]), axis=1) * np.sqrt(252) for k in range(yr)]).T
    q = lambda a: '%7.3f %7.3f %7.3f' % tuple(np.percentile(a, [10, 50, 90]))
    print('== %s  P=%d  (p10 / median / p90 over paths)' % (label, r.shape[0]))
    print(' premium over rf (arith, /yr) ', q(prem))
    print(' volatility (/yr)             ', q(vol))
    print(' worst drawdown 1x            ', q(mdd), ' P(mdd<=-50%%)=%.2f P(mdd<=-70%%)=%.2f' % (np.mean(mdd <= -0.5), np.mean(mdd <= -0.7)))
    print(' 1x hold after-tax CAGR       ', q(h1))
    print(' mean short rate (/yr)        ', q(rf.mean(axis=1) * 252), ' y10 mean %', q(y.mean(axis=1)))
    print(' spread y10-R (/yr)           ', q((y / 100 - rf * 252).mean(axis=1)))
    print(' sd of yearly vol / mean vol  ', q(vy.std(axis=1) / vy.mean(axis=1)))
    print(' annual return std            ', q(ra.std(axis=1)))
    k = np.log1p(r); kk = ((k - k.mean(1, keepdims=True)) ** 4).mean(1) / k.var(1) ** 2
    print(' daily kurtosis               ', q(kk))
    return dict(prem=prem, vol=vol, mdd=mdd, h1=h1)


if __name__ == '__main__':
    import time
    T = 300 + 30 * 252
    for mech in (True, False):
        t0 = time.time()
        d = simulate(2000, T, 1, mechanism=mech)
        print('simulate(2000, %d) mechanism=%s: %.1f s' % (T, mech, time.time() - t0))
        describe(d, 'mechanism %s' % ('ON' if mech else 'OFF'))
