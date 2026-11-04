"""Dealer Ledger simulator (lane TS1, designer L2). See THEORY.md for the theory and the frozen priors.

simulate(P, T, seed, mechanism=True) -> dict(r=(P,T) simple daily index price returns, r[:,0]=0,
                                             rf=(P,T) daily simple short rate, y10=(P,T) 10y yield in percent,
                                             params=dict of per-path parameter arrays)
Every path draws its own parameters from the frozen prior.  mechanism=False gives the mechanism-off world of THEORY.md
section 7 (same parameters, same random numbers, same short-rate path, same realised volatility scale, no ledger).
Pure numpy, vectorised over paths; the time loop is over days.
"""
import numpy as np

BURN = 500
SQ = np.sqrt(252.0)


# frozen prior ranges (THEORY.md section 6) and hard validity bounds used only for the narrowed/widened robustness priors
PRIOR = dict(sigma0=(0.12, 0.26), lam0=(0.8, 3.0), dy0=(0.01, 0.05), L0=(1.5, 5.0), psi=(0.0, 1.0), HLk=(0.5, 5.0),
             klam=(0.2, 1.2), HLv=(10.0, 120.0), sv=(0.0, 0.45), df=(3.0, 12.0), m_r=(0.0, 0.08), HLr=(1.0, 8.0),
             v_r=(0.005, 0.025), tp0=(-0.005, 0.025), HLtp=(0.5, 4.0), sd_tp=(0.002, 0.010), tp_x=(0.0, 0.008),
             c_ts=(0.0, 12.0), D_b=(0.0, 25.0), b_r=(0.0, 4.0))
HARD = dict(sigma0=(0.04, 0.6), lam0=(0.1, 6.0), dy0=(0.0, 0.08), L0=(1.0, 10.0), psi=(0.0, 1.5), HLk=(0.15, 10.0),
            klam=(0.0, 2.5), HLv=(3.0, 300.0), sv=(0.0, 0.9), df=(2.5, 30.0), m_r=(-0.01, 0.15), HLr=(0.3, 15.0),
            v_r=(0.001, 0.05), tp0=(-0.02, 0.05), HLtp=(0.1, 8.0), sd_tp=(0.0005, 0.02), tp_x=(0.0, 0.016),
            c_ts=(0.0, 24.0), D_b=(0.0, 50.0), b_r=(0.0, 8.0))


def draw_params(P, g, width=1.0):
    def U(name):
        a, b = PRIOR[name]
        if width != 1.0:
            m, h = 0.5 * (a + b), 0.5 * (b - a) * width
            a, b = max(m - h, HARD[name][0]), min(m + h, HARD[name][1])
        return g.uniform(a, b, P)
    p = {}
    for name in ('sigma0', 'lam0', 'dy0', 'L0', 'psi', 'HLk', 'klam', 'HLv', 'sv', 'df', 'm_r', 'HLr', 'v_r', 'tp0',
                 'HLtp', 'sd_tp', 'tp_x', 'c_ts', 'D_b', 'b_r'):
        p[name] = U(name)
    p['monthly'] = g.uniform(0, 1, P) < 0.4
    # derived
    p['prem0'] = np.minimum(p['lam0'] * p['sigma0'] ** 2, 0.10)
    p['m_p'] = p['prem0'] - p['dy0']
    p['kappa'] = np.log(2) / p['HLk']
    p['k'] = p['prem0'] * p['klam'] / (p['kappa'] + p['dy0'])
    p['A0'] = 1.0 / (1.0 - np.minimum(p['L0'] * p['k'], 0.75))
    p['s_f0'] = p['sigma0'] / p['A0']
    return p


def simulate(P, T, seed, mechanism=True, return_state=False, width=1.0):
    g = np.random.default_rng(int(seed))
    p = draw_params(P, g, width)
    N = T + BURN
    # AR(1) coefficients
    phv = np.exp(-np.log(2) / p['HLv'])
    a_r = np.log(2) / p['HLr']; phr = np.exp(-a_r / 252)
    sdr = p['v_r'] * np.sqrt((1 - phr ** 2) / (2 * a_r))           # exact discretisation of the OU short rate
    phtp = np.exp(-np.log(2) / (p['HLtp'] * 252))
    F = (1 - np.exp(-10 * a_r)) / (10 * a_r)
    lam5 = 0.5 ** (1.0 / (5 * 252))
    kk, L0, psi, kap = p['k'], p['L0'], p['psi'], p['kappa']
    c_ts, D_b, b_r, tp_x, tp0 = p['c_ts'], p['D_b'], p['b_r'], p['tp_x'], p['tp0']
    m_r, m_p, sv, s_f0 = p['m_r'], p['m_p'], p['sv'], p['s_f0']
    tscale = np.sqrt((p['df'] - 2) / p['df'])
    mon = p['monthly']

    rlog = np.zeros((P, N)); RF = np.zeros((P, N)); Y = np.zeros((P, N)); Yoff = np.zeros((P, N))
    EPS = np.zeros((P, N), dtype=np.float32); SF = np.zeros((P, N), dtype=np.float32)
    XS = np.zeros((P, N), dtype=np.float32) if return_state else None
    AS = np.zeros((P, N), dtype=np.float32) if return_state else None
    SBS = np.zeros((P, N), dtype=np.float32) if return_state else None

    x = np.zeros(P); h = np.zeros(P); u = m_r.copy(); tpn = np.zeros(P)
    rf = np.maximum(u, 0.0)
    y10 = m_r + (rf - m_r) * F + tp0
    y10o = y10.copy()
    sbar = y10 - rf
    RF[:, 0] = rf; Y[:, 0] = y10; Yoff[:, 0] = y10o
    for t in range(1, N):
        zv = g.standard_normal(P); zr = g.standard_normal(P); zt = g.standard_normal(P)
        eps = g.standard_t(p['df']) * tscale
        h = phv * h + np.sqrt(1 - phv ** 2) * sv * zv
        u = m_r + phr * (u - m_r) + sdr * zr
        tpn = phtp * tpn + np.sqrt(1 - phtp ** 2) * p['sd_tp'] * zt
        rf_raw = np.maximum(u, 0.0)
        base = m_r + (rf_raw - m_r) * F + tp0 + tpn
        y_raw = base + tp_x * (-x)
        step = (~mon) | (t % 21 == 0)
        rf_new = np.where(step, rf_raw, rf)
        y_new = np.where(step, y_raw, y10)
        yo_new = np.where(step, base, y10o)
        drf = rf_new - rf; dy = y_new - y10
        s_prev = y10 - rf
        # ledger
        Lt = L0 * np.exp(-psi * x)
        LK = np.minimum(Lt * kk, 0.75)
        A = 1.0 / (1.0 - LK)
        Leff = LK / kk
        sf = s_f0 * np.exp(h - sv ** 2)
        f = sf * eps / SQ
        o = c_ts * (s_prev - sbar) / 252 - D_b * dy - kap * x / 252
        dx = A * (Leff * (f - b_r * drf) + o)
        xn = np.clip(x + dx, -2.5, 1.5)
        dx = xn - x
        rl = (rf_new + m_p) / 252 - 0.5 * (A * sf) ** 2 / 252 + f + kk * dx - b_r * drf
        sbar = lam5 * sbar + (1 - lam5) * s_prev
        x = xn; rf = rf_new; y10 = y_new; y10o = yo_new
        rlog[:, t] = rl; RF[:, t] = rf; Y[:, t] = y10; Yoff[:, t] = y10o
        EPS[:, t] = eps; SF[:, t] = sf
        if return_state:
            XS[:, t] = x; AS[:, t] = A; SBS[:, t] = sbar

    sl = slice(BURN, N)
    rlog = rlog[:, sl]; RF = RF[:, sl]; Y = Y[:, sl]; Yoff = Yoff[:, sl]
    EPS = EPS[:, sl].astype(np.float64); SF = SF[:, sl].astype(np.float64)
    if not mechanism:
        ex_on = rlog[:, 1:] - RF[:, 1:] / 252
        raw = SF[:, 1:] * EPS[:, 1:] / SQ
        c_p = ex_on.std(axis=1) / np.maximum(raw.std(axis=1), 1e-12)
        so = c_p[:, None] * SF
        rlog = (RF + m_p[:, None]) / 252 - 0.5 * so ** 2 / 252 + so * EPS / SQ
        Y = Yoff
        p['c_p'] = c_p
    r = np.expm1(rlog); r[:, 0] = 0.0
    out = dict(r=r, rf=RF / 252.0, y10=100.0 * Y, params=p)
    if return_state:
        out['x'] = XS[:, sl].astype(np.float64); out['A'] = AS[:, sl].astype(np.float64)
        out['sf'] = SF; out['sbar'] = SBS[:, sl].astype(np.float64)   # diagnostic state (oracle only)
    return out


def _describe(d, label):
    r, rf, y = d['r'], d['rf'], d['y10']
    W = 300
    lr = np.log1p(r[:, W:]); ex = lr - rf[:, W:]
    vol = ex.std(axis=1) * SQ
    mex = (r[:, W:] - rf[:, W:]).mean(axis=1) * 252
    # 1-year non-overlapping excess log returns: predictive autocorrelation
    P, n = ex.shape; ny = n // 252
    yr = ex[:, :ny * 252].reshape(P, ny, 252).sum(axis=2)
    a1 = [np.corrcoef(yr[i, :-1], yr[i, 1:])[0, 1] for i in range(P)]
    # vol clustering: corr of |daily| at lag 20
    ab = np.abs(ex)
    ac20 = np.mean([np.corrcoef(ab[i, :-20], ab[i, 20:])[0, 1] for i in range(min(P, 300))])
    q = lambda v: '%.3f/%.3f/%.3f' % tuple(np.percentile(v, [10, 50, 90]))
    print(f'[{label}] paths={P} years={n/252:.1f}')
    print('  ann vol (p10/med/p90)            ', q(vol))
    print('  ann mean simple excess (p10/50/90)', q(mex))
    print('  rf annual mean per path          ', q(rf[:, W:].mean(axis=1) * 252))
    print('  y10 mean per path (%)            ', q(y[:, W:].mean(axis=1)))
    print('  spread y10-rf mean (%)           ', q(y[:, W:].mean(axis=1) - 100 * 252 * rf[:, W:].mean(axis=1)))
    print('  1y->1y excess autocorr (mean, med)  %.3f  %.3f' % (np.nanmean(a1), np.nanmedian(a1)))
    print('  |r| lag-20 autocorr (mean)       %.3f' % ac20)
    print('  worst 1y excess log (p10/50/90)  ', q(yr.min(axis=1)))


if __name__ == '__main__':
    import sys, time
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
    P, T = 2000, 7860
    t0 = time.time(); on = simulate(P, T, 1, True, return_state=True); t1 = time.time()
    off = simulate(P, T, 1, False); t2 = time.time()
    print('sim time ON %.1fs OFF %.1fs' % (t1 - t0, t2 - t1))
    pr = on['params']
    for kname in ('prem0', 'm_p', 'k', 'A0', 's_f0', 'kappa'):
        print('  param %-6s p10/med/p90 %s' % (kname, '%.3f/%.3f/%.3f' % tuple(np.percentile(pr[kname], [10, 50, 90]))))
    x = on['x'][:, 300:]; A = on['A'][:, 300:]
    print('  ledger x sd per path (p10/med/p90) %.3f/%.3f/%.3f' % tuple(np.percentile(x.std(axis=1), [10, 50, 90])))
    print('  amplification A (p10/med/p90 of path means) %.2f/%.2f/%.2f, share of days A>=3.9: %.3f'
          % (*np.percentile(A.mean(axis=1), [10, 50, 90]), np.mean(A >= 3.9)))
    print('  share of days x at clip: %.4f' % np.mean((x <= -2.499) | (x >= 1.499)))
    _describe(on, 'ON'); _describe(off, 'OFF')
    for lab, d in (('ON', on), ('OFF', off)):
        for lev in (1, 2, 3):
            s = ee.summary(ee.hold(d['r'], d['rf'], lev))
            print(f'  {lab} hold {lev}x: cagr_med {s["cagr_med"]:.4f} p10 {s["cagr_p10"]:.4f} p90 {s["cagr_p90"]:.4f} '
                  f'mdd_med {s["mdd_med"]:.3f} p_dd80 {s["p_dd80"]:.3f}')
