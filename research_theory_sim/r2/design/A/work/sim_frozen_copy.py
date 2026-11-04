"""Risk-Meter Leverage Clock (RMLC) simulator - lane TS2 round 2, designer A.

simulate(P, T, seed, mechanism=True) -> dict(r=(P,T) simple daily index returns (price index, r[:,0]=0),
                                             rf=(P,T) simple daily risk-free rate, y10=(P,T) percent, params=dict)
Every parameter is drawn PER PATH from the frozen prior in THEORY.md section 7.  The unconditional level
(premium mu_g, volatility sigma, rf path, news df nu, news innovations) is drawn first from the seed, so the
mechanism-ON and mechanism-OFF worlds of the same seed share it.  No market data of any kind is used.
"""
import numpy as np

TRADING_DAYS = 252


def _loguni(g, lo, hi, n):
    return np.exp(g.uniform(np.log(lo), np.log(hi), n))


def _rates(g, P, T):
    """annual short-rate level paths with long trending regimes and stable regimes (brief 2d)."""
    yrs_seg_lo, yrs_seg_hi = 2.0, 15.0
    lvl = np.empty((P, T))
    for i in range(P):
        start = g.uniform(0.005, 0.07)
        out = np.empty(T); t0 = 0; cur = start
        while t0 < T:
            n = int(g.uniform(yrs_seg_lo, yrs_seg_hi) * TRADING_DAYS)
            n = max(1, min(n, T - t0))
            u = g.uniform()
            if u < 0.3:
                d = g.uniform(0.01, 0.06)
            elif u < 0.6:
                d = -g.uniform(0.01, 0.06)
            else:
                d = 0.0
            out[t0:t0 + n] = cur + d * (np.arange(1, n + 1) / n)
            cur = out[t0 + n - 1]; t0 += n
        lvl[i] = out
    z = np.mod(lvl, 0.24)                                  # reflect into [0, 0.12]
    lvl = np.where(z <= 0.12, z, 0.24 - z)
    phi = 1 - 1 / 60.0                                     # AR(1) wiggle, stationary sd 0.25 %
    e = g.normal(0.0, 0.0025 * np.sqrt(1 - phi ** 2), (P, T))
    w = np.empty((P, T)); w[:, 0] = g.normal(0, 0.0025, P)
    for t in range(1, T):
        w[:, t] = phi * w[:, t - 1] + e[:, t]
    ann = np.clip(lvl + w, 0.0, 0.13)
    monthly = g.uniform(size=P) < 0.5                      # half of the paths move in monthly steps
    idx = (np.arange(T) // 21) * 21
    ann = np.where(monthly[:, None], ann[:, idx], ann)
    # 10y yield (percent): half the current rate, half its 2-year EWMA, plus a term spread and noise
    a = 1 - np.exp(np.log(0.5) / (2 * TRADING_DAYS))
    ew = np.empty((P, T)); ew[:, 0] = ann[:, 0]
    for t in range(1, T):
        ew[:, t] = (1 - a) * ew[:, t - 1] + a * ann[:, t]
    spread = g.uniform(0.005, 0.02, P)
    phi2 = 1 - 1 / 120.0
    e2 = g.normal(0.0, 0.003 * np.sqrt(1 - phi2 ** 2), (P, T))
    w2 = np.empty((P, T)); w2[:, 0] = 0.0
    for t in range(1, T):
        w2[:, t] = phi2 * w2[:, t - 1] + e2[:, t]
    y10 = 100 * np.clip(0.5 * ann + 0.5 * ew + spread[:, None] + w2, 0.0, None)
    return ann / TRADING_DAYS, y10, monthly


def draw_level(g, P):
    mu = np.clip(g.normal(0.015, 0.020, P), -0.03, 0.07)
    # truncation by redraw for the tails (keeps the shape inside the bounds)
    for _ in range(20):
        bad = (mu <= -0.03) | (mu >= 0.07)
        if not bad.any(): break
        mu[bad] = g.normal(0.015, 0.020, bad.sum())
    mu = np.clip(mu, -0.03, 0.07)
    sig = np.exp(g.normal(np.log(0.17), 0.25, P))
    for _ in range(20):
        bad = (sig < 0.09) | (sig > 0.40)
        if not bad.any(): break
        sig[bad] = np.exp(g.normal(np.log(0.17), 0.25, bad.sum()))
    sig = np.clip(sig, 0.09, 0.40)
    nu = g.uniform(4.0, 8.0, P)
    return mu, sig, nu


def draw_mech(g, P):
    return dict(
        k0=g.uniform(0.6, 0.9, P),
        a_v=_loguni(g, 1 / 1000, 1 / 150, P),
        c=g.uniform(0.0, 0.15, P),
        h_g=_loguni(g, 20, 120, P),
        S0=_loguni(g, 0.01, 0.04, P),
        lam_norm=g.uniform(1.5, 3.5, P),
        h_M=_loguni(g, 10, 60, P),
        b=g.uniform(0.0, 0.2, P),
        a_dn=_loguni(g, 0.05, 0.5, P),
        a_up=_loguni(g, 0.005, 0.05, P),
        zeta=_loguni(g, 1 / 1000, 1 / 250, P),
        psi=_loguni(g, 2.0, 6.0, P),
    )


def _mech_path(eps, mu, sig, mp, record=False):
    """agent model in pre-scale units; returns demeaned log returns x (P,T) and optional state history."""
    P, T = eps.shape
    sd = sig / np.sqrt(TRADING_DAYS)                     # speculators' normal daily vol (sigma_ref)
    sf = mp['k0'] * sd                                   # news vol
    mud = mu / TRADING_DAYS
    av, c = mp['a_v'], mp['c']
    ag = 1 - np.exp(np.log(0.5) / mp['h_g'])
    bM = 1 - np.exp(np.log(0.5) / mp['h_M'])
    ln = mp['lam_norm']; Wb = mp['S0'] / ln; lmax = 1.5 * ln
    bb, adn, aup, zt, psi = mp['b'], mp['a_dn'], mp['a_up'], mp['zeta'], mp['psi']
    m = np.zeros(P); gtr = np.zeros(P); M = sd ** 2; W = Wb.copy(); S = ln * Wb
    x = np.zeros((P, T))
    hist = dict(S=np.zeros((P, T)), W=np.zeros((P, T)), M=np.zeros((P, T)), m=np.zeros((P, T)), dS=np.zeros((P, T))) \
        if record else None
    for t in range(1, T):
        lam = np.minimum(lmax, ln * sd / np.sqrt(M))
        Ss = lam * W
        dS = np.where(S > Ss * (1 + bb), -adn * (S - Ss), np.where(S < Ss, aup * (Ss - S), 0.0))
        news = sf * eps[:, t]
        xt = news - av * m * (1 + (m / 0.3) ** 2) + c * gtr + psi * dS
        xt = np.clip(xt, -0.25, 0.25)
        Sn = np.maximum(S + dS, 0.0)
        Rx = np.expm1(xt + mud)
        W = (W + 0.5 * (S + Sn) * Rx) / (1 + Rx)
        W = W + zt * (Wb - W)
        W = np.clip(W, 0.1 * Wb, 2 * Wb)
        S = np.minimum(Sn, 0.3)
        M = (1 - bM) * M + bM * xt * xt
        gtr = (1 - ag) * gtr + ag * xt
        m = m + xt - news
        x[:, t] = xt
        if record:
            hist['S'][:, t] = S; hist['W'][:, t] = W; hist['M'][:, t] = M; hist['m'][:, t] = m; hist['dS'][:, t] = dS
    return x, hist


def simulate(P, T, seed, mechanism=True, record=False, level_override=None):
    """level_override: optional dict(mu=..., sig=...) scalars or (P,) arrays, used only for prior-narrow/wide checks."""
    g = np.random.default_rng(int(seed))
    mu, sig, nu = draw_level(g, P)
    if level_override is not None:
        if 'mu' in level_override: mu = np.broadcast_to(np.asarray(level_override['mu'], float), (P,)).copy()
        if 'sig' in level_override: sig = np.broadcast_to(np.asarray(level_override['sig'], float), (P,)).copy()
    rf, y10, monthly = _rates(g, P, T)
    eps = g.standard_t(nu[:, None], size=(P, T)) * np.sqrt((nu[:, None] - 2) / nu[:, None])
    mp = draw_mech(g, P)                                  # drawn in both worlds so the streams stay aligned
    hist = None
    if mechanism:
        x, hist = _mech_path(eps, mu, sig, mp, record=record)
    else:
        x = eps * (sig[:, None] / np.sqrt(TRADING_DAYS))
        x[:, 0] = 0.0
    sd = sig / np.sqrt(TRADING_DAYS)
    scale = sd / np.maximum(x[:, 1:].std(axis=1), 1e-12)  # realised vol of the path = drawn sigma
    x = x * scale[:, None]
    lr = np.log1p(rf) + (mu / TRADING_DAYS)[:, None] + x
    r = np.expm1(lr); r[:, 0] = 0.0
    params = dict(mu_g=mu, sigma=sig, nu=nu, rf_monthly=monthly, scale=scale, mechanism=bool(mechanism))
    if mechanism: params.update(mp)
    out = dict(r=r, rf=rf, y10=y10, params=params)
    if record: out['hist'] = hist
    return out


def describe(sim, warm=300):
    """descriptive statistics of a simulated world (they describe the theory; they are not targets)."""
    import sys
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
    import exec_engine as ee
    r, rf = sim['r'], sim['rf']
    lr = np.log1p(r[:, warm:]); lf = np.log1p(rf[:, warm:])
    prem = (lr - lf).mean(axis=1) * TRADING_DAYS
    vol = lr.std(axis=1) * np.sqrt(TRADING_DAYS)
    cp = np.cumsum(lr, axis=1)
    dd = (cp - np.maximum.accumulate(np.maximum(cp, 0.0), axis=1)).min(axis=1)
    mdd = np.expm1(dd)
    h1 = ee.hold(r, rf, 1)['cagr']
    q = lambda a: '%+.3f [p10 %+.3f, p90 %+.3f]' % (np.median(a), np.percentile(a, 10), np.percentile(a, 90))
    # monthly skew and squared-return autocorrelation (clustering)
    nm = lr.shape[1] // 21
    mr = lr[:, :nm * 21].reshape(lr.shape[0], nm, 21).sum(axis=2)
    mz = (mr - mr.mean(1, keepdims=True)) / mr.std(1, keepdims=True)
    skew = (mz ** 3).mean(1)
    a2 = lr - lr.mean(1, keepdims=True); s2 = a2 ** 2; s2 = s2 - s2.mean(1, keepdims=True)
    ac2 = (s2[:, 1:] * s2[:, :-1]).mean(1) / (s2 ** 2).mean(1)
    d = (a2 / a2.std(1, keepdims=True))
    kurt = (d ** 4).mean(1)
    lines = ['premium (log, /yr)        ' + q(prem), 'volatility (/yr)          ' + q(vol),
             'worst drawdown (30y)      ' + q(mdd),
             'P(worst DD <= -50%%)       %.3f' % np.mean(mdd <= -0.5), 'P(worst DD <= -75%%)       %.3f' % np.mean(mdd <= -0.75),
             'hold 1x after-tax CAGR    ' + q(h1), 'rf mean (annual)          ' + q(rf[:, warm:].mean(1) * TRADING_DAYS),
             'monthly skew              ' + q(skew), 'daily kurtosis            ' + q(kurt),
             'acf1 of squared returns   ' + q(ac2)]
    return '\n'.join(lines), dict(prem=prem, vol=vol, mdd=mdd, h1=h1, skew=skew, kurt=kurt, ac2=ac2)


if __name__ == '__main__':
    import time, sys
    P = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    T = 300 + 30 * 252
    for mech in (True, False):
        t0 = time.time(); s = simulate(P, T, 1, mechanism=mech); t1 = time.time()
        txt, _ = describe(s)
        print('=== mechanism %s  (P=%d, T=%d, %.1fs)' % ('ON' if mech else 'OFF', P, T, t1 - t0))
        print(txt)
