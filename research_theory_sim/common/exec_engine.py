"""Execution + tax model for ALL design work in research/theory_sim (lane TS1).
It applies exactly the same trading, cost and tax rules as the engine that will later run the frozen rule on real data.
It contains NO market data. Pure numpy, vectorised over paths (arrays have shape (P, T)).

Instrument set (spot only, no margin):
  a 3x daily-leveraged product on the equity index  +  a USD cash deposit.
  A target level L in [0, 3] is held as weight L/3 in the 3x product and 1 - L/3 in cash
  (L = 1 is one-third 3x product + two-thirds cash, i.e. index exposure 1.0).
  3x product daily return = 3*r - 2*rf - 0.0245/252      r  = index simple daily return (price index, no dividends)
                                                          rf = daily risk-free rate (simple, per day)
  cash daily return       = max(rf - 0.02/252, 0) * (1 - 0.154)   (deposit spread 2%/yr, 15.4% interest tax)
Orders:  the level is held in 0.5 steps; it changes only when |target - held| >= 0.5, or when target == 0 (full exit).
Delay:   a target decided with data up to close t is traded at close t+2 (earns from day t+3).  delay=2 by default.
Cost:    0.3% of traded notional per trade (fee 0.25% + spread 0.05%).
Tax:     22% of each 252-day tax year's net realised gain above a deduction of 0.25 x initial capital, paid at the start
         of the next tax year by a proportional sale; no loss carry-forward; at each tax-year end, losses/gains are
         harvested up to the deduction when worth it; on the last day the unrealised gain is taxed too (liquidation tax).
Paths:   the first WARM = 300 columns are warm-up (signal history only, no trading, no P&L).
         Standard horizon: T = 300 + 30*252 = 7860 columns -> 30 years.  Set r[:, 0] = 0.

API
  run(r, rf, B, delay=2, cost=0.003, curve=False) -> dict(cagr=(P,), final=(P,), mdd=(P,), w7=(P,), w12=(P,),
                                                          trades_per_year=(P,), avg_level=(P,), curve=(P,T-WARM) or None)
      B = target level (P, T) decided at close t (NaN -> 0 = cash; clipped to [0, 3]).
  hold(r, rf, lev) -> dict(cagr, final, mdd, w7, w12)   same-basis buy-and-hold baselines (lev 1, 2 or 3)
  summary(res) -> dict(median CAGR, p10, p90, mean log growth, P(MDD<=-80%), P(MDD<=-95%), median MDD, ...)

Headline objective used everywhere in this project: the MEDIAN over paths of the 30-year after-tax CAGR
(after the final liquidation tax) = summary(res)['cagr_med'].
"""
import numpy as np

WARM = 300
F1 = dict(delay=2, cost=0.003, tax=0.22, D=0.25, harvest=3, hthr=1.0, cspr=0.02, er3=0.0095 + 0.015, step=0.5, fstep=0.5)


def run(r, rf, B, delay=2, cost=0.003, curve=False, **kw):
    p = dict(F1); p.update(kw); p['delay'] = int(delay); p['cost'] = float(cost)
    r = np.ascontiguousarray(r, dtype=np.float64); rf = np.ascontiguousarray(rf, dtype=np.float64)
    B = np.ascontiguousarray(B, dtype=np.float64)
    if r.ndim == 1: r, rf, B = r[None, :], rf[None, :], B[None, :]
    P, T = r.shape
    if T <= WARM + 252: raise ValueError('need T > WARM + 252 columns')
    dl, cost, tax, D = p['delay'], p['cost'], p['tax'], p['D']
    harvest, hthr, cspr, er3, step, fstep = int(p['harvest']), p['hthr'], p['cspr'], p['er3'], p['step'], p['fstep']
    z = np.zeros(P)
    v0 = z.copy(); v3 = z.copy(); b0 = z.copy(); real = z.copy()
    held = z.copy(); cur = np.full(P, -99.0)
    q = np.zeros((P, dl + 1))
    E = np.ones(P); gpk = np.ones(P); mdd = z.copy(); E7 = np.full(P, np.nan); E12 = np.full(P, np.nan)
    ntr = z.copy(); levsum = z.copy(); nk = 0
    EE = np.zeros((P, T - WARM)) if curve else None
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:                       # tax for the year just ended, paid by proportional sale
                due = tax * np.maximum(real - D, 0.0); real = z.copy()
                m = due > 0
                if m.any():
                    tot = v0 + v3
                    f = np.where(m, np.minimum(due / np.maximum(tot, 1e-300), 1.0), 0.0)
                    real = real + f * (v0 - b0)
                    v0 = v0 * (1 - f); v3 = v3 * (1 - f); b0 = b0 * (1 - f)
            want = q[:, 0].copy()
            for j in range(dl - 1): q[:, j] = q[:, j + 1]
            if k > 0:
                v0 = v0 * (1 + 3 * r[:, t] - 2 * rf[:, t] - er3 / 252)
                v3 = v3 * (1 + np.maximum(rf[:, t] - cspr / 252, 0.0) * (1 - 0.154))
            m = want != cur
            if m.any():
                tot = v0 + v3
                if k == 0:
                    tot = np.where(m, 1.0, tot); v3 = np.where(m, 1.0, v3)
                w0 = want / 3
                t0 = w0 * tot; t3 = (1 - w0) * tot
                d0 = t0 - v0
                tc = cost * np.abs(d0)
                sell = m & (d0 < 0) & (v0 > 0)
                fr = np.where(sell, np.minimum(-d0 / np.where(v0 > 0, v0, 1.0), 1.0), 0.0)
                real = real + fr * (v0 - b0)
                b0 = np.where(sell, b0 * (1 - fr), b0)
                b0 = np.where(m & (d0 > 0), b0 + d0, b0)
                sc = (tot - tc) / np.maximum(tot, 1e-300)
                v0 = np.where(m, t0 * sc, v0); v3 = np.where(m, t3 * sc, v3)
                cur = np.where(m, want, cur); ntr = ntr + m
            if harvest > 0 and k % 252 == 251:               # tax-year-end harvest up to the deduction
                mh = v0 > 1e-12
                target = D - real; U = v0 - b0
                Us = np.where(U != 0, U, 1.0)
                f = np.zeros(P)
                if harvest & 1: f = np.where((target < 0) & (U < 0), np.minimum(1.0, target / Us), f)
                if harvest & 2: f = np.where((target > 0) & (U > 0), np.minimum(1.0, target / Us), f)
                f = np.where(mh, f, 0.0)
                rz = f * U; sv = f * v0
                ok = mh & (sv > 0) & (tax * np.abs(rz) > hthr * 2 * cost * sv)
                tc = 2 * cost * sv
                real = np.where(ok, real + rz, real)
                b0 = np.where(ok, b0 - (sv - rz) + (sv - tc), b0)
                v0 = np.where(ok, v0 - tc, v0)
            E = v0 + v3
            gpk = np.maximum(gpk, E); mdd = np.minimum(mdd, E / gpk - 1)
            if k == 7 * 252 - 1: E7 = E.copy()
            if k == 12 * 252 - 1: E12 = E.copy()
            levsum = levsum + np.where(cur > 0, cur, 0.0); nk += 1
            if curve: EE[:, k] = E
        # decision at close t (identity: target = B)
        tg = B[:, t]
        tg = np.where(np.isnan(tg), 0.0, tg)
        tg = np.clip(tg, 0.0, 3.0)
        stp = np.where((tg >= 1.0) | (held >= 1.0), step, fstep)
        ch = (np.abs(tg - held) >= stp) | ((tg == 0) & (held > 0))
        held = np.where(ch, np.round(tg / stp) * stp, held)
        if t == WARM - 1:
            q[:, :dl] = held[:, None]
        elif t >= WARM:
            q[:, dl - 1] = held
    unr = v0 - b0
    fin = E - tax * np.maximum(real + unr - D, 0.0)
    yrs = (T - WARM) / 252
    return dict(cagr=np.maximum(fin, 1e-9) ** (1 / yrs) - 1, final=fin, mdd=mdd, w7=E7, w12=E12,
                trades_per_year=ntr / yrs, avg_level=levsum / max(nk, 1), curve=EE)


def hold(r, rf, lev, tax=0.22):
    """same-basis buy-and-hold: lev 1 (fee 0.2%/yr), lev 2 (2r - rf - 2.45%/yr), lev 3 (through run() with B = 3)."""
    r = np.asarray(r, dtype=np.float64); rf = np.asarray(rf, dtype=np.float64)
    if r.ndim == 1: r, rf = r[None, :], rf[None, :]
    if lev == 3:
        return run(r, rf, np.full(r.shape, 3.0))
    rr = r[:, WARM:]; ff = rf[:, WARM:]
    x = rr - 0.002 / 252 if lev == 1 else lev * rr - (lev - 1) * ff - (0.0095 + 0.015) / 252
    Ec = np.cumprod(1 + x, axis=1); yrs = Ec.shape[1] / 252
    fin = Ec[:, -1] * (1 - 0.003) - tax * np.maximum(Ec[:, -1] * (1 - 0.003) - 1, 0)
    pk = np.maximum.accumulate(np.maximum(Ec, 1.0), axis=1)
    mdd = np.minimum((Ec / pk - 1).min(axis=1), 0.0)
    return dict(cagr=np.maximum(fin, 1e-9) ** (1 / yrs) - 1, final=fin, mdd=mdd, w7=Ec[:, 7 * 252 - 1], w12=Ec[:, 12 * 252 - 1])


def summary(res):
    c = np.asarray(res['cagr']); m = np.asarray(res['mdd'])
    out = dict(cagr_med=float(np.median(c)), cagr_p10=float(np.percentile(c, 10)), cagr_p90=float(np.percentile(c, 90)),
               mean_log_growth=float(np.mean(np.log1p(c))), mdd_med=float(np.median(m)),
               p_dd80=float(np.mean(m <= -0.8)), p_dd95=float(np.mean(m <= -0.95)), n_paths=int(c.size))
    if 'w7' in res: out['w7_med'] = float(np.nanmedian(res['w7']))
    if 'w12' in res: out['w12_med'] = float(np.nanmedian(res['w12']))
    if 'trades_per_year' in res: out['trades_per_year_med'] = float(np.median(res['trades_per_year']))
    if 'avg_level' in res: out['avg_level_med'] = float(np.median(res['avg_level']))
    return out


if __name__ == '__main__':      # self-check on pure noise (no market data): runs, shapes, holds
    g = np.random.default_rng(0); P, T = 200, WARM + 30 * 252
    r = g.normal(0.0003, 0.012, (P, T)); r[:, 0] = 0; rf = np.full((P, T), 0.03 / 252)
    for lev in (1, 2, 3): print('hold', lev, summary(hold(r, rf, lev)))
    print('B=1.5 const', summary(run(r, rf, np.full((P, T), 1.5))))
