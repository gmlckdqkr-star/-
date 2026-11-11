"""xeng: beng.run1 (the locked v1 account engine) extended by J extra instruments held next to the 3x NDX fund.

With all extra target weights zero it must reproduce beng.run1 exactly (t_xeng_parity.py). Same rules for the extras:
decision at close t in force after `delay` days, cost per side on traded notional, average cost basis, one yearly 22% tax
on the net realised gain of the whole account above the deduction, proportional sale to pay it. Idle cash earns
max(rf - cspr, 0) after 15.4% (cspr = 10.0 -> zero).

Extras:  G (T, J) daily returns of the instruments (net of their own fund costs), Wt (T, J) target weights of total
account equity decided at close t (signal only; the engine decides what is affordable).
mode 0: v1 has priority. The 3x NDX fund gets want/3 of the account whenever v1's level changes; extras may only use
        cash that v1 leaves idle and are cut pro rata when v1 needs it back.
mode 1: extras have priority. They get their target weight; the 3x NDX fund gets want/3 of what is left.
inc 0: a changed target weight w means 'hold w of the account now' (rebalance to it).
inc 1: tranche semantics. A higher target adds (new - old) of the account as fresh money and leaves earlier tranches alone;
       a lower target sells the position pro rata (to zero when the target is zero). Money put in never exceeds the target sum.
rec columns: 0 equity E (after costs and paid taxes), 1 v1 level in force, 2 brake target, 3 base signal,
             4 liquidation value (E minus tax on all realised + unrealised gains so far), 5 sum of extra weights."""
import numpy as np
from numba import njit
WARM = 300


@njit
def runx(r, rf, B, feat, G, Wt, mode, inc, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, rec, fstep):
    T = r.shape[0]; J = G.shape[1]
    v0 = 0.0; v3 = 0.0; b0 = 0.0
    ve = np.zeros(J); be = np.zeros(J); curw = np.zeros(J); te = np.zeros(J)
    real = 0.0; due = 0.0
    held = 0.0; cur = -99.0
    q = np.zeros(delay + 1); qw = np.zeros((delay + 1, J)); wantw = np.zeros(J)
    st = np.zeros(32)
    kpk = 1.0; E = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                due = tax * max(real - D, 0.0); real = 0.0
                if due > 0:
                    tot = v0 + v3 + ve.sum(); taxp += due
                    f = min(due / max(tot, 1e-300), 1.0)
                    real += f * (v0 - b0)
                    for j in range(J):
                        real += f * (ve[j] - be[j]); ve[j] *= (1 - f); be[j] *= (1 - f)
                    v0 *= (1 - f); v3 *= (1 - f); b0 *= (1 - f)
                    due = 0.0
            want = q[0]
            for j in range(J): wantw[j] = qw[0, j]
            for i in range(delay - 1):
                q[i] = q[i + 1]
                for j in range(J): qw[i, j] = qw[i + 1, j]
            if k > 0:
                v0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
                v3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
                for j in range(J): ve[j] *= (1 + G[t, j])
            chg_l = want != cur
            chg_w = False
            for j in range(J):
                if wantw[j] != curw[j]: chg_w = True
            if chg_l or chg_w:
                tot = v0 + v3 + ve.sum()
                if k == 0:
                    tot = 1.0; v3 = 1.0
                w0 = want / 3
                se = 0.0
                for j in range(J):
                    if wantw[j] == curw[j]: te[j] = ve[j]
                    elif inc == 0: te[j] = wantw[j] * tot
                    elif wantw[j] > curw[j]: te[j] = ve[j] + (wantw[j] - curw[j]) * tot      # add a tranche, never top up old ones
                    else: te[j] = ve[j] * (wantw[j] / curw[j]) if curw[j] > 0 else 0.0           # sell pro rata
                    if te[j] < 0: te[j] = 0.0
                    se += te[j]
                if mode == 0:
                    t0 = w0 * tot if chg_l else v0
                    room = tot - t0
                    if room < 0: room = 0.0
                    if se > room:
                        sc_e = room / se if se > 0 else 0.0
                        for j in range(J): te[j] *= sc_e
                        se = room
                else:
                    if se > tot:
                        sc_e = tot / se
                        for j in range(J): te[j] *= sc_e
                        se = tot
                    t0 = w0 * (tot - se) if (chg_l or chg_w) else v0
                t3 = tot - t0 - se
                d0 = t0 - v0
                tc = cost * abs(d0)
                if d0 < 0 and v0 > 0:
                    fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                if d0 > 0: b0 += d0
                for j in range(J):
                    dj = te[j] - ve[j]
                    tc += cost * abs(dj)
                    if dj < 0 and ve[j] > 0:
                        fr = min(-dj / ve[j], 1.0); real += fr * (ve[j] - be[j]); be[j] *= 1 - fr
                    if dj > 0: be[j] += dj
                costp += tc
                sc = (tot - tc) / max(tot, 1e-300)
                v0 = t0 * sc; v3 = t3 * sc
                for j in range(J):
                    ve[j] = te[j] * sc; curw[j] = wantw[j]
                if chg_l:
                    cur = want; ntr += 1
            if harvest > 0 and k % 252 == 251 and v0 > 1e-12:
                target = D - real
                U = v0 - b0
                f = 0.0
                if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                rz = f * U; sv = f * v0
                if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                    tc = 2 * cost * sv; costp += tc
                    real += rz; b0 = b0 - (sv - rz) + (sv - tc)
                    v0 -= tc
            E = v0 + v3 + ve.sum()
            kpk = max(kpk, E)
        b = B[t]
        if np.isnan(b): b = 0.0
        tg = bfn(t - WARM, E, kpk, b, held, feat[t], st, bp)
        if np.isnan(tg): tg = 0.0
        if tg > 3.0: tg = 3.0
        if tg < 0.0: tg = 0.0
        stp = step if (tg >= 1.0 or held >= 1.0) else fstep
        if abs(tg - held) >= stp or (tg == 0 and held > 0):
            held = np.round(tg / stp) * stp
        if t == WARM - 1:
            for i in range(delay):
                q[i] = held
                for j in range(J): qw[i, j] = 0.0
        elif t >= WARM:
            q[delay - 1] = held
            for j in range(J):
                w = Wt[t, j]
                if np.isnan(w): w = 0.0
                qw[delay - 1, j] = w
        if t >= WARM:
            unr = v0 - b0
            se = 0.0
            for j in range(J):
                unr += ve[j] - be[j]; se += ve[j]
            rec[t - WARM, 0] = E; rec[t - WARM, 1] = cur; rec[t - WARM, 2] = tg; rec[t - WARM, 3] = b
            rec[t - WARM, 4] = E - due - tax * max(real + unr - D, 0.0)
            rec[t - WARM, 5] = se / max(E, 1e-300)
    return ntr, taxp, costp


def run(r, rf, B, feat, bfn, bp, G=None, Wt=None, mode=0, inc=0, **kw):
    """single path. returns rec (T - WARM, 6)."""
    import beng
    p, D = beng._args(kw); T = len(r)
    if G is None: G = np.zeros((T, 1)); Wt = np.zeros((T, 1))
    rec = np.zeros((T - WARM, 6))
    runx(np.ascontiguousarray(r), np.ascontiguousarray(rf), np.ascontiguousarray(B, dtype=np.float64), np.ascontiguousarray(feat),
         np.ascontiguousarray(G, dtype=np.float64), np.ascontiguousarray(Wt, dtype=np.float64), int(mode), int(inc), int(p['delay']), p['cost'],
         p['tax'], D, int(p['harvest']), p['hthr'], p['cspr'], p['er3'], p['step'], bfn, np.asarray(bp, dtype=np.float64), rec,
         float(p['fstep']))
    return rec
