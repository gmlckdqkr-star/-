"""Independent pure-Python re-statement of the MS1 account arithmetic (BRIEF section 1 / beng docstring) on the single-path
bases. The brake (rx.av23s) is called as a black box; everything else (3x product, cash yield, cost, yearly 22% tax with
deduction, year-end harvest, final liquidation tax, delay queue, 0.5/0.1 steps) is written out here in plain Python.
Purposes: (1) check that the STACK terms act as their labels say (cash yield written explicitly, not through cspr);
(2) NBR caveat: sub-accounts with ONE shared tax book (yearly netting across sub-accounts, one deduction) vs own books."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, rx, bk, beng, ce
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
import strat as S_lib
OUT = '/mnt/project-files/research/final1/verify_main/results/'
WARM = 300; TAX = 0.22; DED = 2.5e6 / 10e6; ER3 = 0.0245; STEP = 0.5; FSTEP = 0.1
BP = np.asarray(rx.P_av23s(.85), dtype=np.float64)

class Acct:
    def __init__(s, delay):
        s.v0 = 0.0; s.v3 = 0.0; s.b0 = 0.0; s.real = 0.0; s.held = 0.0; s.cur = -99.0
        s.q = [0.0] * (delay + 1); s.st = np.zeros(32); s.kpk = 1.0; s.E = 1.0; s.delay = delay; s.curve = []

def simulate(r, rf, Bs, feat, cash_yield, cost, delay=2, joint=False):
    """Bs: list of base-signal arrays (one per sub-account). cash_yield(rf_t) -> daily after-tax cash return.
    joint=False: every sub-account has its own tax book and deduction DED (per unit start) = the std engine.
    joint=True : one tax book: yearly tax = 22% x max(sum of realized - N x DED, 0), paid pro rata by all sub-accounts."""
    N = len(Bs); A = [Acct(delay) for _ in range(N)]; T = len(r); due = [0.0] * N
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                if joint:
                    dtot = TAX * max(sum(a.real for a in A) - N * DED, 0.0)
                    for a in A: a.real = 0.0
                    if dtot > 0:
                        tot = sum(a.v0 + a.v3 for a in A); f = min(dtot / max(tot, 1e-300), 1.0)
                        for a in A:
                            a.real += f * (a.v0 - a.b0); a.v0 *= 1 - f; a.v3 *= 1 - f; a.b0 *= 1 - f
                else:
                    for a in A:
                        d = TAX * max(a.real - DED, 0.0); a.real = 0.0
                        if d > 0:
                            tot = a.v0 + a.v3; f = min(d / max(tot, 1e-300), 1.0)
                            a.real += f * (a.v0 - a.b0); a.v0 *= 1 - f; a.v3 *= 1 - f; a.b0 *= 1 - f
            for a in A:
                want = a.q[0]
                for j in range(a.delay - 1): a.q[j] = a.q[j + 1]
                if k > 0:
                    a.v0 *= 1 + 3 * r[t] - 2 * rf[t] - ER3 / 252
                    a.v3 *= 1 + cash_yield(rf[t])
                if want != a.cur:
                    tot = a.v0 + a.v3
                    if k == 0: tot = 1.0; a.v3 = 1.0
                    t0 = want / 3 * tot; d0 = t0 - a.v0; tc = cost * abs(d0)
                    if d0 < 0 and a.v0 > 0:
                        fr = min(-d0 / a.v0, 1.0); a.real += fr * (a.v0 - a.b0); a.b0 *= 1 - fr
                    if d0 > 0: a.b0 += d0
                    sc = (tot - tc) / max(tot, 1e-300)
                    a.v0 = t0 * sc; a.v3 = (tot - t0) * sc; a.cur = want
            if k % 252 == 251:                                   # year-end harvest towards the deduction
                if joint:
                    target = N * DED - sum(a.real for a in A)
                    for a in A:
                        if a.v0 <= 1e-12: continue
                        U = a.v0 - a.b0; f = 0.0
                        if target < 0 and U < 0: f = min(1.0, target / U)
                        if target > 0 and U > 0: f = min(1.0, target / U)
                        rz = f * U; sv = f * a.v0
                        if sv > 0 and TAX * abs(rz) > 2 * cost * sv:
                            tc = 2 * cost * sv; a.real += rz; a.b0 = a.b0 - (sv - rz) + (sv - tc); a.v0 -= tc; target -= rz
                else:
                    for a in A:
                        if a.v0 <= 1e-12: continue
                        target = DED - a.real; U = a.v0 - a.b0; f = 0.0
                        if target < 0 and U < 0: f = min(1.0, target / U)
                        if target > 0 and U > 0: f = min(1.0, target / U)
                        rz = f * U; sv = f * a.v0
                        if sv > 0 and TAX * abs(rz) > 2 * cost * sv:
                            tc = 2 * cost * sv; a.real += rz; a.b0 = a.b0 - (sv - rz) + (sv - tc); a.v0 -= tc
            for a in A:
                a.E = a.v0 + a.v3; a.kpk = max(a.kpk, a.E); a.curve.append(a.E)
        for i, a in enumerate(A):                                 # decision at close t
            b = Bs[i][t]
            if np.isnan(b): b = 0.0
            tg = rx.av23s(t - WARM, a.E, a.kpk, b, a.held, feat[t], a.st, BP)
            if np.isnan(tg): tg = 0.0
            tg = min(max(tg, 0.0), 3.0)
            stp = STEP if (tg >= 1.0 or a.held >= 1.0) else FSTEP
            if abs(tg - a.held) >= stp or (tg == 0 and a.held > 0): a.held = float(np.round(tg / stp) * stp)
            if t == WARM - 1:
                for j in range(a.delay): a.q[j] = a.held
            elif t >= WARM:
                a.q[a.delay - 1] = a.held
    yrs = (T - WARM) / 252.0
    if joint:
        fin = sum(a.E for a in A) - TAX * max(sum(a.real + a.v0 - a.b0 for a in A) - N * DED, 0.0)
        fin /= N
    else:
        fin = float(np.mean([a.E - TAX * max(a.real + a.v0 - a.b0 - DED, 0.0) for a in A]))
    Em = np.mean([a.curve for a in A], axis=0)
    return max(fin, 1e-9) ** (1 / yrs) - 1, float((Em / np.maximum.accumulate(Em) - 1).min())

y_base = lambda rf: max(rf - 0.02 / 252, 0.0) * (1 - 0.154)     # MS1: (rf - 2pp) x (1 - 15.4%)
y_zero = lambda rf: 0.0                                         # S1/S5: idle USD earns nothing
y_rp = lambda rf: max(rf - 0.005 / 252, 0.0) * (1 - 0.154)      # S2/S4: rf - 0.5pp, taxed 15.4%
ROWS = {'S0_base': (y_base, 0.003, 2), 'S1_CASH0': (y_zero, 0.003, 2), 'S2_CASHRP': (y_rp, 0.003, 2), 'S3_FEE': (y_base, 0.0012, 2),
        'S4_CASHRP_FEE': (y_rp, 0.0012, 2), 'S5_CASH0_FEE': (y_zero, 0.0012, 2), 'S8_delay1_CASHRP_FEE': (y_rp, 0.0012, 1)}
NBR5 = [(200, .40), (180, .40), (220, .40), (200, .35), (200, .45)]
NBR9 = [(sl, v) for sl in (180, 200, 220) for v in (.35, .40, .45)]

