"""MS1-condition sleeve engine (numba kernel). Imported ONLY inside the MS1 worker process (lab/ms1.py serve()),
never by lab's core or bar processes.

It is research/c3_brake/code/beng.py run1 (the engine std.measure uses through c3_combo ce.runPE, parameters beng.F1)
with the single 'TQQQ l/3 + USD cash' position replaced by the spec's own sleeve weights (QQQ, QLD, TQQQ + cash).
Every MS1 section-1 rule is kept as beng implements it:
  - day loop from WARM (300): k = t - WARM; no return on k = 0 (the account opens all cash and buys at close k = 0).
  - tax year = 252 simulated days: at k % 252 == 0 (k > 0) pay tax * max(realized - D, 0) (22%, D = 2.5M / 10M =
    0.25 start units, no loss carry-forward) by a proportional sale of every holding incl. cash (the sale's realized
    gain goes to the new year); realized gain = average cost basis.
  - year end (k % 252 == 251, harvest = 3): if realized < D, realize unrealized gains up to D (sell + rebuy, 2 x cost);
    if realized > D, realize unrealized losses down to D; only when tax x |realized| > 2 x cost x amount sold. With
    several sleeves, gains (losses) are taken pro rata from the sleeves that have them (one sleeve: exactly beng).
  - decision at close t -> trade at close t + 2 (delay queue as beng: both slots hold the decision of WARM - 1 at
    start). A trade happens when the target weights change (or on a forced rebalance row of the spec's
    `rebalance:` cadence); cost 0.3% x |traded notional| of the risk sleeves (cash moves are free), both legs' values
    scaled by (total - cost) / total as in beng. No 0.5-level order step: the spec's weights are traded as given
    (beng rounds a 0..3 level to 0.5 steps, 0.1 below 1x with fstep 0.1).
  - returns: QQQ r - 0.2%/252, QLD 2r - rf - (0.95% + 1.5%)/252, TQQQ 3r - 2rf - (0.95% + 1.5%)/252,
    cash max(rf - 2%/252, 0) x (1 - 15.4%) (computed by the caller, see ms1._sleeve_returns).
  - end: fin = equity - tax * max(realized + unrealized - D, 0) (liquidation tax, no exit cost: beng has none).
"""
import numpy as np
from numba import njit, prange

WARM = 300


@njit(cache=True)
def run1(R, CR, W, FORCE, delay, cost, tax, D, harvest, hthr, Erec):
    T, S = R.shape
    v = np.zeros(S); b = np.zeros(S); cash = 0.0
    real = 0.0
    q = np.zeros((delay + 1, S)); qf = np.zeros(delay + 1)
    cur = np.full(S, -99.0); held = np.zeros(S)
    E = 1.0; ntr = 0.0
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                due = tax * max(real - D, 0.0); real = 0.0
                if due > 0:
                    tot = cash
                    for s in range(S):
                        tot += v[s]
                    f = min(due / max(tot, 1e-300), 1.0)
                    for s in range(S):
                        real += f * (v[s] - b[s]); v[s] *= (1 - f); b[s] *= (1 - f)
                    cash *= (1 - f)
            want = q[0].copy(); fw = qf[0]
            for j in range(delay - 1):
                q[j] = q[j + 1]; qf[j] = qf[j + 1]
            if k > 0:
                for s in range(S):
                    v[s] *= 1 + R[t, s]
                cash *= 1 + CR[t]
            chg = fw > 0 or k == 0
            for s in range(S):
                if want[s] != cur[s]:
                    chg = True
            if chg:
                tot = cash
                for s in range(S):
                    tot += v[s]
                if k == 0:
                    tot = 1.0; cash = 1.0
                tc = 0.0
                for s in range(S):
                    d = want[s] * tot - v[s]
                    tc += cost * abs(d)
                    if d < 0 and v[s] > 0:
                        fr = min(-d / v[s], 1.0); real += fr * (v[s] - b[s]); b[s] *= 1 - fr
                    if d > 0:
                        b[s] += d
                sc = (tot - tc) / max(tot, 1e-300)
                ws = 0.0
                for s in range(S):
                    v[s] = want[s] * tot * sc; ws += want[s]; cur[s] = want[s]
                cash = (1 - ws) * tot * sc
                ntr += 1
            if harvest > 0 and k % 252 == 251:
                target = D - real
                uneg = 0.0; upos = 0.0
                for s in range(S):
                    if v[s] > 1e-12:
                        u = v[s] - b[s]
                        if u < 0:
                            uneg += u
                        else:
                            upos += u
                f = 0.0; sign = 0
                if target < 0 and uneg < 0 and (harvest & 1):
                    f = min(1.0, target / uneg); sign = -1
                if target > 0 and upos > 0 and (harvest & 2):
                    f = min(1.0, target / upos); sign = 1
                if f > 0:
                    rz = 0.0; sv = 0.0
                    for s in range(S):
                        u = v[s] - b[s]
                        if v[s] > 1e-12 and ((sign < 0 and u < 0) or (sign > 0 and u > 0)):
                            rz += f * u; sv += f * v[s]
                    if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                        real += rz
                        for s in range(S):
                            u = v[s] - b[s]
                            if v[s] > 1e-12 and ((sign < 0 and u < 0) or (sign > 0 and u > 0)):
                                svs = f * v[s]; rzs = f * u; tcs = 2 * cost * svs
                                b[s] = b[s] - (svs - rzs) + (svs - tcs)
                                v[s] -= tcs
            E = cash
            for s in range(S):
                E += v[s]
            Erec[t - WARM] = E
        for s in range(S):                       # decision at close t (the spec's weights, NaN -> 0)
            x = W[t, s]
            held[s] = 0.0 if np.isnan(x) else x
        if t == WARM - 1:
            for j in range(delay):
                q[j] = held.copy(); qf[j] = 0.0
        elif t >= WARM:
            q[delay - 1] = held.copy(); qf[delay - 1] = 1.0 if FORCE[t] else 0.0
    unr = 0.0
    for s in range(S):
        unr += v[s] - b[s]
    return E - tax * max(real + unr - D, 0.0), ntr


@njit(parallel=True, cache=True)
def runP(R, CR, W, FORCE, delay, cost, tax, D, harvest, hthr):
    """R, W: (P, T, S) sleeve returns / decided weights; CR: (P, T) cash return; FORCE: (P, T) bool forced-rebalance
    decision rows. -> fin (P,) after liquidation tax, EE (P, T - WARM) equity, trades (P,)."""
    P, T, S = R.shape
    fin = np.zeros(P); EE = np.zeros((P, T - WARM)); ntr = np.zeros(P)
    for i in prange(P):
        f, n = run1(R[i], CR[i], W[i], FORCE[i], delay, cost, tax, D, harvest, hthr, EE[i])
        fin[i] = f; ntr[i] = n
    return fin, EE, ntr


@njit(parallel=True, cache=True)
def series_run(M, Q, real_share, cost, tax, D):
    """IS1 stream engine (research/indiv_stock/code/eng.py run, without its turnover / dividend drag: the stream is
    already after cost, and a stock stream already after the dividend tax): M (P, T) daily returns after WARM; Q (P, T)
    the part of each day's return that is reinvested cash already taxed (a stock's dividend after its 15.4% tax), per
    unit of the previous day's value: added to the cost basis (zeros for a price stream). Entry cost, every 252 days
    tax * max(real_share x unrealized - D, 0) on the realized share (no carry-forward), exit cost and liquidation tax
    at the end; unrealized = value - basis, so a dividend is never taxed at 22%."""
    P, T = M.shape
    fin = np.zeros(P); EE = np.zeros((P, T))
    for i in prange(P):
        Wv = 1.0 - cost; Bv = Wv
        for t in range(T):
            Bv = Bv + Wv * Q[i, t]
            Wv = Wv * (1.0 + M[i, t])
            if (t + 1) % 252 == 0 and t + 1 < T:
                Rz = real_share * (Wv - Bv); tx = tax * max(Rz - D, 0.0)
                Bv = Bv + Rz - tx; Wv = Wv - tx
            EE[i, t] = Wv
        f = Wv * (1.0 - cost); Bv = Bv - Wv * cost
        fin[i] = f - tax * max(f - Bv - D, 0.0)
    return fin, EE
