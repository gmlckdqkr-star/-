"""Synthetic market for the Margin-Ratchet Leverage Cycle (MRLC) theory (lane TS1, designer L1).

simulate(P, T, seed, mechanism=True) -> dict(r=(P,T) simple daily index returns, rf=(P,T) simple daily short rate,
                                            y10=None, params=dict of per-path parameter arrays)
Every path draws its own parameters from the frozen priors in THEORY.md (each path is a different world).
r[:, 0] = 0. No market data of any kind is used.

Mechanism (see THEORY.md): log p = f + beta*(Q_S + Q_X) + u.
  f: fundamental, drift g0 + chi*R, news sigma_f (Student-t), duration D to short-rate changes.
  Q_S = l*w: leveraged speculators (fractional Kelly on extrapolative beliefs, allowed leverage 1/H with
       H = clip(h_k*M, H_min, 1), M = lender risk memory = ratchet: max(current lender vol, decayed M)).
  Q_X: unlevered trend extrapolators (next-day echo gain b_X).  u: AR(1) sentiment.
  Orders decided at close t move the price on day t+1.
mechanism=False: i.i.d. Student-t(nu) daily log returns with the same per-path mean and std as the ON world.
"""
import numpy as np

LN2 = np.log(2.0)
LCAP = 15.0              # absolute leverage cap (structural constant, THEORY.md section 7)
WCAP = 3.0               # speculator equity share capped at 3*w_bar (amendment A1, THEORY.md)
BURN = 1260              # internal burn-in days (discarded) so the slow state starts near its stationary regime

# frozen priors (THEORY.md section 7): name -> (lo, hi), uniform per path
PRIOR = dict(
    Rbar=(0.00, 0.07), R_hl=(2.0, 12.0), R_vol=(0.004, 0.020),
    g0=(-0.01, 0.06), chi=(0.0, 1.0), D=(0.0, 6.0), sigma_f=(0.07, 0.18), nu=(3.5, 30.0),
    beta=(1.5, 6.0), Phi=(0.01, 0.10), tau_w=(0.5, 4.0),
    c=(0.25, 1.0), m0=(0.04, 0.10), kappa=(0.0, 1.0), tau_x=(40.0, 250.0), tau_v=(10.0, 60.0), s_b=(0.005, 0.03),
    phi_v=(0.02, 0.20), phi_f=(0.2, 1.0),
    h_k=(1.5, 4.0), H_min=(0.08, 0.35), tau_L=(0.5, 5.0), tau_lv=(5.0, 30.0),
    b_X=(0.0, 0.15), tau_X=(20.0, 200.0),
    sigma_u=(0.02, 0.10), hl_u=(0.1, 2.0),
)
P_MONTHLY = 0.5
# hard physical limits used only when the prior is widened for robustness checks
HARD = dict(Rbar=(0.0, 0.15), R_hl=(0.5, 30), R_vol=(0.0005, 0.05), chi=(0.0, 1.0), D=(0.0, 15.0),
            sigma_f=(0.02, 0.40), nu=(2.5, 200.0), beta=(0.3, 15.0), Phi=(0.0, 0.25), tau_w=(0.1, 10.0),
            c=(0.05, 2.0), m0=(0.0, 0.2), kappa=(0.0, 2.0), tau_x=(5, 500), tau_v=(3, 150), s_b=(0.0, 0.06),
            phi_v=(0.005, 0.5), phi_f=(0.05, 1.0), h_k=(0.5, 8.0), H_min=(0.03, 0.8), tau_L=(0.05, 10.0),
            tau_lv=(2, 80), b_X=(0.0, 0.3), tau_X=(5, 400), sigma_u=(0.0, 0.2), hl_u=(0.02, 5.0), g0=(-0.05, 0.12))


def draw_params(P, rng, prior_scale=1.0, prior=None):
    """Draw per-path parameters. prior_scale scales each range's width about its midpoint (1 = frozen prior)."""
    prior = PRIOR if prior is None else prior
    out = {}
    for k, (lo, hi) in prior.items():
        mid, half = 0.5 * (lo + hi), 0.5 * (hi - lo) * prior_scale
        a, b = mid - half, mid + half
        if k in HARD:
            a, b = max(a, HARD[k][0]), min(b, HARD[k][1])
        out[k] = rng.uniform(a, b, P)
    out['monthly'] = rng.uniform(0, 1, P) < P_MONTHLY
    return out


def _rates(P, T, rng, prm):
    k = LN2 / prm['R_hl']
    sd_stat = prm['R_vol'] / np.sqrt(2 * k)
    R = np.clip(prm['Rbar'] + sd_stat * rng.standard_normal(P), 0.0, 0.20)
    out = np.empty((P, T))
    mon = prm['monthly']
    for t in range(T):
        dt = 1.0 / 252
        Rn = R + k * (prm['Rbar'] - R) * dt + prm['R_vol'] * np.sqrt(dt) * rng.standard_normal(P)
        Rn = np.abs(Rn)                                   # reflect at zero
        Rn = np.minimum(Rn, 0.20)
        if t % 21 != 0:                                   # monthly-step paths hold the rate between months
            Rn = np.where(mon, R, Rn)
        else:
            dtm = 21.0 / 252                              # monthly paths take one month of movement at once
            Rm = R + k * (prm['Rbar'] - R) * dtm + prm['R_vol'] * np.sqrt(dtm) * rng.standard_normal(P)
            Rn = np.where(mon, np.minimum(np.abs(Rm), 0.20), Rn)
        R = Rn
        out[:, t] = R
    return out


def _t_unit(rng, nu, P):
    return rng.standard_t(nu, P) * np.sqrt((nu - 2.0) / nu)


def simulate(P, T, seed, mechanism=True, prior_scale=1.0, return_state=False, override=None):
    """override: optional dict name -> value applied after the prior draw (diagnostic decompositions only)."""
    rng = np.random.default_rng(seed)
    prm = draw_params(P, rng, prior_scale)
    if override:
        for k, v in override.items():
            prm[k] = np.broadcast_to(np.asarray(v, dtype=prm[k].dtype), (P,)).copy()
    TT = T + BURN
    Ra = _rates(P, TT, rng, prm)                          # annual short rate path (incl. burn-in)

    beta, Phi = prm['beta'], prm['Phi']
    wbar = Phi / beta
    wfloor = 0.02 * wbar
    sf_d = prm['sigma_f'] / np.sqrt(252)
    su_d = prm['sigma_u'] / np.sqrt(252)
    rho_u = np.exp(-LN2 / (prm['hl_u'] * 252))
    aw = 1 - np.exp(-LN2 / (prm['tau_w'] * 252))
    a_v = 2.0 / (prm['tau_v'] + 1); a_lv = 2.0 / (prm['tau_lv'] + 1)
    a_x = 2.0 / (prm['tau_x'] + 1); a_X = 2.0 / (prm['tau_X'] + 1)
    dL = np.exp(-LN2 / (prm['tau_L'] * 252))
    sdX = sf_d * np.sqrt(a_X / (2 - a_X))
    alphaX = prm['b_X'] * sdX / (beta * a_X)

    # state
    v0 = (prm['sigma_f'] ** 2 + prm['sigma_u'] ** 2) / 252
    vs = v0.copy(); vl = v0.copy(); M = np.sqrt(252 * vl)
    x = np.zeros(P); xX = np.zeros(P); QX = np.zeros(P); u = np.zeros(P)
    w = wbar.copy()
    sp = np.maximum(np.sqrt(252 * vs), 0.03)
    H = np.clip(prm['h_k'] * M, prm['H_min'], 1.0)
    lev = np.minimum(np.clip(prm['c'] * (prm['m0'] - Ra[:, 0] - prm['s_b']) / sp ** 2, 0, 15), 1 / H)
    flow = np.zeros(P)
    rlog = np.zeros((P, T))
    if return_state:
        st = {k: np.zeros((P, T), dtype=np.float32) for k in ('QS', 'M', 'w', 'lev', 'Lmax', 'bk')}
    Rprev = Ra[:, 0]
    for t in range(1, TT):
        R = Ra[:, t]
        eps = _t_unit(rng, prm['nu'], P)
        dfund = (prm['g0'] + prm['chi'] * Rprev) / 252 + sf_d * eps - prm['D'] * (R - Rprev)
        un = rho_u * u + su_d * rng.standard_normal(P)
        r = dfund + (un - u) + beta * flow
        r = np.clip(r, -0.25, 0.25)
        u = un
        # --- end of day t: agents update ---
        Rs = np.expm1(r)
        lm1 = lev - 1
        gross = 1 + lev * Rs - lm1 * Rprev / 252 - np.maximum(lm1, 0) * prm['s_b'] / 252
        Qold = lev * w
        bk = gross <= 0.02
        w_ret = np.where(bk, wfloor, w * gross / (1 + Rs))
        w_fl = w_ret + aw * (wbar - w_ret)
        w_fl = np.minimum(w_fl, WCAP * wbar)              # capacity: equity above WCAP*w_bar is paid out
        bk = bk | (w_fl <= wfloor)
        w_fl = np.maximum(w_fl, wfloor)
        lmech = Qold / w_fl
        bk = bk | (lmech > LCAP)                          # lender closes out positions beyond the absolute cap
        lmech = np.where(bk, 1.0, lmech)
        vs = vs + a_v * (r * r - vs); vl = vl + a_lv * (r * r - vl)
        sp = np.maximum(np.sqrt(252 * vs), 0.03)
        M = np.maximum(np.sqrt(252 * vl), M * dL)
        H = np.clip(prm['h_k'] * M, prm['H_min'], 1.0)
        Lmax = 1.0 / H
        x = x + a_x * (r * 252 - x)
        lstar = np.clip(prm['c'] * (prm['m0'] + prm['kappa'] * x - R - prm['s_b']) / sp ** 2, 0.0, LCAP)
        tgt = np.minimum(lstar, Lmax)
        lvol = lmech + prm['phi_v'] * (tgt - lmech)
        lfor = lmech - prm['phi_f'] * (lmech - Lmax)
        lnew = np.where(lmech > Lmax, np.minimum(lvol, lfor), lvol)
        lnew = np.where(bk, 1.0, np.minimum(lnew, LCAP))
        Qnew = lnew * w_fl
        flowS = np.where(bk, Qnew - Qold, Qnew - Qold)
        xX = xX + a_X * (r - xX)
        QXn = alphaX * np.tanh(xX / sdX)
        flow = flowS + (QXn - QX)
        QX = QXn; lev = lnew; w = w_fl; Rprev = R
        j = t - BURN
        if j >= 0:
            rlog[:, j] = r
            if return_state:
                st['QS'][:, j] = Qnew; st['M'][:, j] = M; st['w'][:, j] = w_fl; st['lev'][:, j] = lnew
                st['Lmax'][:, j] = Lmax; st['bk'][:, j] = bk
    rf = Ra[:, BURN:] / 252
    rlog[:, 0] = 0.0
    if not mechanism:
        WARM = 300
        mu = rlog[:, WARM:].mean(axis=1); sd = rlog[:, WARM:].std(axis=1)
        g2 = np.random.default_rng([seed, 777])
        z = g2.standard_t(prm['nu'][:, None], (P, T)) * np.sqrt((prm['nu'][:, None] - 2) / prm['nu'][:, None])
        rlog = mu[:, None] + sd[:, None] * z
        rlog = np.clip(rlog, -0.25, 0.25)
        rlog[:, 0] = 0.0
    r_simple = np.expm1(rlog)
    r_simple[:, 0] = 0.0
    out = dict(r=r_simple, rf=rf, y10=None, params=prm)
    if return_state and mechanism:
        out['state'] = st
    return out


def describe(sim, label=''):
    r = sim['r'][:, 300:]; lr = np.log1p(r)
    P, n = lr.shape; yrs = n / 252
    vol = lr.std(axis=1) * np.sqrt(252); drift = lr.mean(axis=1) * 252
    z = (lr - lr.mean(axis=1, keepdims=True)) / lr.std(axis=1, keepdims=True)
    skew = (z ** 3).mean(axis=1); kurt = (z ** 4).mean(axis=1) - 3
    a = np.abs(z); a = a - a.mean(axis=1, keepdims=True)
    ac_abs = (a[:, 1:] * a[:, :-1]).mean(axis=1) / (a ** 2).mean(axis=1)
    ac1 = (z[:, 1:] * z[:, :-1]).mean(axis=1)
    cp = np.cumsum(lr, axis=1); dd = cp - np.maximum.accumulate(cp, axis=1); mdd = np.expm1(dd.min(axis=1))
    # 21-day and 252-day return autocorrelation (non-overlapping)
    m21 = cp[:, 20::21]; r21 = np.diff(m21, axis=1)
    q = lambda v: np.percentile(v, [10, 50, 90]).round(4).tolist()
    print(f'--- {label}  P={P} years={yrs:.0f}')
    print(' ann vol p10/50/90      ', q(vol))
    print(' ann log drift p10/50/90', q(drift))
    print(' daily skew p10/50/90   ', q(skew))
    print(' excess kurt p10/50/90  ', q(kurt))
    print(' ac1 daily p10/50/90    ', q(ac1))
    print(' ac |r| lag1 p10/50/90  ', q(ac_abs))
    print(' max drawdown p10/50/90 ', q(mdd))
    print(' share paths MDD<-50%   ', round(float(np.mean(mdd < -0.5)), 3))
    rf = sim['rf'][:, 300:] * 252
    print(' rf mean p10/50/90      ', q(rf.mean(axis=1)))
    if 'state' in sim:
        bk = sim['state']['bk'][:, 300:]
        print(' speculator wipe-outs per path (30y) mean', round(float(bk.sum(axis=1).mean()), 3),
              ' share of paths with >=1:', round(float((bk.sum(axis=1) > 0).mean()), 3))
        L = sim['state']['lev'][:, 300:]
        print(' spec leverage p10/50/90 (time-avg)', q(L.mean(axis=1)))


if __name__ == '__main__':
    import sys, time
    sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
    import exec_engine as ee
    P = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    T = 300 + 30 * 252
    t0 = time.time(); s = simulate(P, T, seed=1, mechanism=True, return_state=True); t1 = time.time()
    print(f'simulate ON P={P} T={T}: {t1 - t0:.1f}s')
    describe(s, 'mechanism ON (seed 1)')
    for lev in (1, 2, 3):
        print(' hold', lev, {k: round(v, 4) for k, v in ee.summary(ee.hold(s['r'], s['rf'], lev)).items()
                             if k in ('cagr_med', 'cagr_p10', 'cagr_p90', 'mdd_med', 'p_dd80')})
    t0 = time.time(); s0 = simulate(P, T, seed=1, mechanism=False); t1 = time.time()
    print(f'simulate OFF: {t1 - t0:.1f}s')
    describe(s0, 'mechanism OFF (seed 1)')
    for lev in (1, 2, 3):
        print(' hold', lev, {k: round(v, 4) for k, v in ee.summary(ee.hold(s0['r'], s0['rf'], lev)).items()
                             if k in ('cagr_med', 'cagr_p10', 'cagr_p90', 'mdd_med', 'p_dd80')})
