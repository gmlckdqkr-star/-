"""Simulator of the SGNC theory (Salience-Gated Narrative Contagion), lane TS1, blind designer L3.

simulate(P, T, seed, mechanism=True, prior='base') -> dict(r=(P,T), rf=(P,T), y10=None, params=dict of (P,) arrays)

Each path draws its own world from the priors frozen in THEORY.md (section 6).  No market data of any kind.
mechanism=True : beliefs about the hidden story spread by Bass-type contagion gated by salience-driven attention.
mechanism=False: same draws and random numbers, but learning is instantaneous (price jumps by dm at story switches),
                 and the ON path's debate-noise variance is replaced by i.i.d. Gaussian noise of equal average variance.
prior = 'base' | 'narrow' (ranges shrunk to 50% around their centre) | 'wide' (ranges stretched to 150%, clamped).
"""
import numpy as np

DT = 1.0 / 252

# name: (lo, hi, log?, clamp_lo, clamp_hi)
PRIORS = {
    'D_up':     (0.5, 8.0, True, 0.2, 20.0),      # years
    'D_dn':     (0.5, 8.0, True, 0.2, 20.0),
    'sigD':     (0.08, 0.22, False, 0.04, 0.35),
    'omega':    (0.05, 0.60, False, 0.01, 0.80),
    'k':        (1.5, 25.0, True, 0.5, 60.0),     # per year
    'psi':      (0.0, 0.95, False, 0.0, 0.98),
    'eta':      (0.0, 1.5, False, 0.0, 2.5),
    'hs':       (5.0, 40.0, False, 2.0, 80.0),    # days
    'sig_n':    (0.0, 1.5, False, 0.0, 2.5),
    'prem':     (0.01, 0.08, False, -0.01, 0.12),
    'divy':     (0.00, 0.05, False, 0.0, 0.07),
    'rf_mu':    (0.00, 0.07, False, 0.0, 0.10),
    'rf_hl':    (2.0, 15.0, True, 1.0, 30.0),     # years
    'rf_sd':    (0.005, 0.03, False, 0.001, 0.05),
    'sv_hl':    (20.0, 500.0, True, 10.0, 1000.0),  # days
    'sv_sd':    (0.0, 0.5, False, 0.0, 0.8),
    'df':       (3.0, 12.0, False, 2.5, 30.0),
    'u_sd':     (0.0, 0.02, False, 0.0, 0.03),
    'u_hl':     (1.0, 10.0, False, 0.5, 20.0),    # days
}
P_MONTHLY_RF = 0.3
X_LO, X_HI = 0.01, 0.99
LONG_HL = 250.0


def _draw(g, P, name, prior):
    lo, hi, lg, clo, chi = PRIORS[name]
    sc = {'base': 1.0, 'narrow': 0.5, 'wide': 1.5}[prior]
    if lg:
        a, b = np.log(lo), np.log(hi)
        m, h = 0.5 * (a + b), 0.5 * (b - a) * sc
        v = np.exp(g.uniform(m - h, m + h, P))
    else:
        m, h = 0.5 * (lo + hi), 0.5 * (hi - lo) * sc
        v = g.uniform(m - h, m + h, P)
    return np.clip(v, clo, chi)


def draw_params(g, P, prior='base'):
    p = {n: _draw(g, P, n, prior) for n in PRIORS}
    p['rf_monthly'] = g.random(P) < P_MONTHLY_RF
    nu = 2.0 / (p['D_up'] + p['D_dn'])                       # story switches per year
    p['dm'] = np.minimum(p['sigD'] * np.sqrt(p['omega'] / (1 - p['omega']) / nu), 1.0)
    p['c'] = p['psi'] * p['k']; p['p'] = (1 - p['psi']) * p['k']
    return p


def simulate(P, T, seed, mechanism=True, prior='base', diag=False):
    g = np.random.default_rng(seed)
    pr = draw_params(g, P, prior)
    h_up, h_dn = 1.0 / pr['D_up'], 1.0 / pr['D_dn']
    dm = pr['dm']
    g_up_x = h_up * (1 - np.exp(-dm))          # rational-consistency growth add-ons
    g_dn_x = h_dn * (np.exp(dm) - 1)
    # rf: OU in annual units
    phi_rf = np.exp(-np.log(2) * DT / pr['rf_hl']); inn_rf = pr['rf_sd'] * np.sqrt(1 - phi_rf ** 2)
    rf_lat = pr['rf_mu'] + pr['rf_sd'] * g.standard_normal(P)
    # fundamental stochastic vol (log AR(1)), E[v^2] = 1
    phi_v = np.exp(-np.log(2) / pr['sv_hl']); inn_v = pr['sv_sd'] * np.sqrt(1 - phi_v ** 2)
    lv = pr['sv_sd'] * g.standard_normal(P)
    tsc = np.sqrt(pr['df'] / (pr['df'] - 2))
    # liquidity noise
    phi_u = np.exp(-np.log(2) / pr['u_hl']); inn_u = pr['u_sd'] * np.sqrt(1 - phi_u ** 2)
    u = pr['u_sd'] * g.standard_normal(P)
    # state
    s = np.where(g.random(P) < pr['D_up'] / (pr['D_up'] + pr['D_dn']), 1.0, -1.0)
    x = np.where(s > 0, X_HI, X_LO); xo = x.copy()
    a_s = 1 - 0.5 ** (1 / pr['hs']); a_l = 1 - 0.5 ** (1 / LONG_HL)
    ews = pr['sigD'] * np.sqrt(DT) * 0.8; ewl = ews.copy()
    talkvar = np.zeros(P)
    sqdt = np.sqrt(DT)
    r_on = np.zeros((P, T)); dl_off = np.zeros((P, T)); rf = np.zeros((P, T))
    if diag:
        S_st = np.zeros((P, T), np.int8); X_st = np.zeros((P, T), np.float32)
    rf_ann = np.clip(rf_lat, 0.0, 0.2); rf[:, 0] = rf_ann / 252
    for t in range(1, T):
        # rates
        rf_lat = pr['rf_mu'] + phi_rf * (rf_lat - pr['rf_mu']) + inn_rf * g.standard_normal(P)
        new_rf = np.clip(rf_lat, 0.0, 0.2)
        rf_ann = np.where(pr['rf_monthly'] & (t % 21 != 0), rf_ann, new_rf)
        rf[:, t] = rf_ann / 252
        # story switch
        hz = np.where(s > 0, h_up, h_dn) * DT
        s = np.where(g.random(P) < hz, -s, s)
        up = s > 0
        # fundamentals
        lv = phi_v * lv + inn_v * g.standard_normal(P)
        volD = pr['sigD'] * np.exp(lv - pr['sv_sd'] ** 2)
        R = rf_ann + pr['prem'] - pr['divy']
        gs = np.where(up, R + g_up_x, R - g_dn_x)
        eD = g.standard_t(pr['df']) / tsc
        dlogD = (gs - 0.5 * volD ** 2) * DT + volD * sqdt * eD
        # ON beliefs: Bass diffusion gated by salience, plus debate noise
        a = np.clip(ews / ewl, 0.25, 4.0) ** pr['eta']
        drift = np.where(up, (pr['p'] + pr['c'] * x) * (1 - x), -(pr['p'] + pr['c'] * (1 - x)) * x)
        sx = pr['sig_n'] * x * (1 - x)
        talkvar += (dm * sx) ** 2 * a * DT
        xn = np.clip(x + a * DT * drift + sx * np.sqrt(a * DT) * g.standard_normal(P), X_LO, X_HI)
        # liquidity noise
        un = phi_u * u + inn_u * g.standard_normal(P)
        dlp = dlogD + dm * (xn - x) + (un - u)
        xon = np.where(up, X_HI, X_LO)
        dl_off[:, t] = dlogD + dm * (xon - xo) + (un - u)
        r = np.expm1(np.maximum(dlp, -3.0))
        r_on[:, t] = r
        ar = np.abs(r)
        ews = ews + a_s * (ar - ews); ewl = ewl + a_l * (ar - ewl)
        x, xo, u = xn, xon, un
        if diag:
            S_st[:, t] = s; X_st[:, t] = x
    if mechanism:
        rr = r_on
    else:
        sd_iid = np.sqrt(talkvar / (T - 1))
        z = g.standard_normal((P, T)) * sd_iid[:, None]
        dl_off += z - 0.5 * sd_iid[:, None] ** 2
        rr = np.expm1(np.maximum(dl_off, -3.0))
    rr[:, 0] = 0.0
    out = dict(r=rr, rf=rf, y10=None, params=pr)
    if diag:
        out['state'] = S_st; out['x'] = X_st
    return out


def describe(sim, label=''):
    """descriptive statistics of a batch of synthetic worlds (they describe the theory, they are not targets)."""
    r = sim['r'][:, 300:]; lr = np.log1p(r)
    P, T = lr.shape
    ann_mu = lr.mean(1) * 252; ann_sd = lr.std(1) * np.sqrt(252)
    def vr(h):
        n = T // h
        agg = lr[:, :n * h].reshape(P, n, h).sum(2)
        return agg.var(1) / (h * lr.var(1))
    m21 = lr[:, :(T // 21) * 21].reshape(P, -1, 21).sum(2)
    ac1m = np.array([np.corrcoef(m[:-1], m[1:])[0, 1] for m in m21])
    k = ((lr - lr.mean(1, keepdims=True)) ** 4).mean(1) / lr.var(1) ** 2
    # vol clustering: autocorrelation of |r| at lag 5
    ab = np.abs(lr - lr.mean(1, keepdims=True))
    acab = np.array([np.corrcoef(a[:-5], a[5:])[0, 1] for a in ab])
    q = lambda v: '%.3f/%.3f/%.3f' % tuple(np.percentile(v, [10, 50, 90]))
    print(f'--- {label}  P={P}  years={T/252:.0f}   (p10/median/p90 over paths)')
    print('  ann mean log return :', q(ann_mu))
    print('  ann vol             :', q(ann_sd))
    print('  daily kurtosis      :', q(k))
    print('  AC(1m returns)      :', q(ac1m))
    print('  VR(21)  VR(126) VR(252):', q(vr(21)), q(vr(126)), q(vr(252)))
    print('  AC(|r|, lag 5)      :', q(acab))
    print('  rf mean (ann)       :', q(sim['rf'][:, 300:].mean(1) * 252))
    pr = sim['params']
    print('  dm (valuation gap)  :', q(pr['dm']), '  switches/yr:', q(2 / (pr['D_up'] + pr['D_dn'])))


if __name__ == '__main__':
    import time
    T = 300 + 30 * 252
    t0 = time.time(); on = simulate(2000, T, 1, True); t1 = time.time()
    print(f'simulate(2000, {T}) ON took {t1 - t0:.1f}s')
    describe(on, 'mechanism ON (seed 1)')
    del on
    off = simulate(2000, T, 1, False)
    describe(off, 'mechanism OFF (seed 1)')
