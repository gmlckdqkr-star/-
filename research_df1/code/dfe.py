"""DF1 multi-asset after-tax engine (PRECOMMIT_DF1.md section 1). MS1 conventions copied from c3_brake/code/beng.py run1:
same day order (yearly tax at k%252==0 by proportional sale, delay queue, returns, rebalance on change, year-end harvest,
decision at close t), same cost / tax / deduction / final liquidation tax. Products:
  asset 0 T  : 3x NDX  = 3r - 2rf - er3/252
  asset 1 Q  : 1x NDX  = r - erq/252
  asset 2 BD : 10y Treasury ETF = rb - erb/252, coupon part cpn taxed 15.4% when accrued (basis += after-tax coupon)
  asset 3 TB : T-bill ETF = (rf - ertb/252), all income, taxed 15.4% when accrued (basis grows with it -> no capital gain)
  cash       : max(rf - cspr/252, 0) * (1 - 0.154)   (cspr = 10 -> 0, user rule)
vmode 0 (DF): L<=1 -> Q=L, risk-off asset = 1-L ; L>1 -> T=(L-1)/2, Q=1-T.   vmode 1 (beng parity): T = L/3, cash rest.
  vmode 2 (DF2 M2): T = L/3, risk-off asset = 1 - L/3.
roff: 0 cash, 1 T-bill ETF, 2 bond ETF, 3 bond if bondup[t] else T-bill ETF.
knee: m = clip((DD-d1)/(d0-d1),0,1), m >= kfl when idxup[t]; DD from account E / running max (beng kpk). kon=0 -> off.
All decisions use information at close t only; executed at close t+delay (beng queue)."""
import numpy as np
from numba import njit, prange
WARM = 300

@njit(cache=True)
def _w(L, a, vmode):
    w = np.zeros(4)
    if vmode == 1:
        w[0] = L / 3.0
        return w
    if vmode == 2:                       # DF2 M2: equity exposure through TQQQ, the freed capital in the risk-off asset
        w[0] = L / 3.0
        if a >= 1: w[a] = 1.0 - L / 3.0
        return w
    if L <= 1.0:
        w[1] = L
        if a >= 1: w[a] = 1.0 - L        # a = 2 bond, 3 T-bill ; a = 0 -> cash
    else:
        w[0] = (L - 1.0) / 2.0; w[1] = 1.0 - w[0]
    return w

@njit(cache=True)
def run1(r, rf, rb, cpn, idxup, bondup, Ltg, delay, cost, tax, D, harvest, hthr, cspr, er3, erq, erb, ertb,
         step_hi, step_lo, roff, vmode, kon, d0, d1, kfl, reb_every, out, rec, recon):
    T = r.shape[0]
    v = np.zeros(4); b = np.zeros(4); vc = 0.0
    real = 0.0; due = 0.0
    held = 0.0; cur = -99.0; cura = -1
    qL = np.zeros(delay + 1); qA = np.zeros(delay + 1, dtype=np.int64)
    kpk = 1.0; gpk = 1.0; mdd = 0.0; E = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0
    E7 = np.nan; E12 = np.nan; levsum = 0.0; nk = 0.0
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                due = tax * max(real - D, 0.0); real = 0.0
                if due > 0:
                    tot = v[0] + v[1] + v[2] + v[3] + vc; taxp += due
                    f = min(due / max(tot, 1e-300), 1.0)
                    for i in range(4):
                        real += f * (v[i] - b[i]); v[i] *= (1 - f); b[i] *= (1 - f)
                    vc *= (1 - f)
                    due = 0.0
            want = qL[0]; wa = qA[0]
            for j in range(delay - 1):
                qL[j] = qL[j + 1]; qA[j] = qA[j + 1]
            if k > 0:
                v[0] *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
                v[1] *= (1 + r[t] - erq / 252)
                ic = cpn[t] * (1 - 0.154)
                b[2] += v[2] * ic
                v[2] *= (1 + rb[t] - erb / 252 - 0.154 * cpn[t])
                y = rf[t] - ertb / 252
                if y > 0: y *= (1 - 0.154)
                b[3] += v[3] * y
                v[3] *= (1 + y)
                vc *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
            ea = wa if (want < 1.0 or (vmode == 2 and want < 3.0)) else 0   # asset identity matters only when something is left for it
            forced = reb_every > 0 and k > 0 and k % reb_every == 0
            if want != cur or ea != cura or forced:
                tot = v[0] + v[1] + v[2] + v[3] + vc
                if k == 0:
                    tot = 1.0; vc = 1.0
                w = _w(want, wa, vmode)
                tc = 0.0
                tg = np.zeros(4)
                for i in range(4):
                    tg[i] = w[i] * tot
                    d = tg[i] - v[i]
                    tc += cost * abs(d)
                    if d < 0 and v[i] > 0:
                        fr = min(-d / v[i], 1.0); real += fr * (v[i] - b[i]); b[i] *= 1 - fr
                    if d > 0: b[i] += d
                costp += tc
                sc = (tot - tc) / max(tot, 1e-300)
                vcash = (1.0 - w[0] - w[1] - w[2] - w[3]) * tot
                for i in range(4): v[i] = tg[i] * sc
                vc = vcash * sc
                cur = want; cura = ea; ntr += 1
            if harvest > 0 and k % 252 == 251:
                for i in range(3):            # T, Q, bond (T-bill ETF never has an unrealised gain)
                    if v[i] > 1e-12:
                        target = D - real
                        U = v[i] - b[i]
                        f = 0.0
                        if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                        if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                        rz = f * U; sv = f * v[i]
                        if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                            tc = 2 * cost * sv; costp += tc
                            real += rz; b[i] = b[i] - (sv - rz) + (sv - tc)
                            v[i] -= tc
            E = v[0] + v[1] + v[2] + v[3] + vc
            gpk = max(gpk, E); mdd = min(mdd, E / gpk - 1)
            if k == 7 * 252 - 1: E7 = E
            if k == 12 * 252 - 1: E12 = E
            levsum += cur if cur > 0 else 0.0; nk += 1
            kpk = max(kpk, E)
        # decision at close t
        tg0 = Ltg[t]
        if np.isnan(tg0): tg0 = 0.0
        if kon == 1:
            dd = E / kpk - 1.0
            m = (dd - d1) / (d0 - d1)
            if m > 1.0: m = 1.0
            if m < 0.0: m = 0.0
            if idxup[t] and m < kfl: m = kfl
            tg0 = tg0 * m
        if tg0 > 3.0: tg0 = 3.0
        if tg0 < 0.0: tg0 = 0.0
        stp = step_hi if (tg0 >= 1.0 or held >= 1.0) else step_lo
        if abs(tg0 - held) >= stp or (tg0 == 0 and held > 0):
            held = np.round(tg0 / stp) * stp
        a = 0                                  # roff 0 cash -> asset id 0 means 'no ETF, cash'
        if roff == 1: a = 3
        if roff == 2: a = 2
        if roff == 3:
            a = 2 if bondup[t] else 3
        if t == WARM - 1:
            for j in range(delay):
                qL[j] = held; qA[j] = a
        elif t >= WARM:
            qL[delay - 1] = held; qA[delay - 1] = a
        if recon == 1 and t >= WARM:
            rec[t - WARM] = E
    unr = 0.0
    for i in range(4): unr += v[i] - b[i]
    fin = E - due - tax * max(real + unr - D, 0.0)
    out[0] = fin; out[1] = mdd; out[2] = E7; out[3] = E12; out[4] = ntr; out[5] = taxp; out[6] = costp; out[7] = E
    out[8] = levsum / max(nk, 1.0)

@njit(parallel=True, cache=True)
def runP(R, RF, RB, CP, IU, BU, L, delay, cost, tax, D, harvest, hthr, cspr, er3, erq, erb, ertb,
         step_hi, step_lo, roff, vmode, kon, d0, d1, kfl, reb_every, recon):
    P, T = R.shape; out = np.zeros((P, 9)); EE = np.zeros((P, T - WARM)) if recon == 1 else np.zeros((P, 1))
    for i in prange(P):
        rec = np.zeros(T - WARM) if recon == 1 else np.zeros(1)
        run1(R[i], RF[i], RB[i], CP[i], IU[i], BU[i], L[i], delay, cost, tax, D, harvest, hthr, cspr, er3, erq, erb, ertb,
             step_hi, step_lo, roff, vmode, kon, d0, d1, kfl, reb_every, out[i], rec, recon)
        if recon == 1: EE[i] = rec
    return out, EE

DEF = dict(delay=2, cost=0.003, tax=0.22, D=0.25, harvest=3, hthr=1.0, cspr=10.0, er3=0.0245, erq=0.002, erb=0.0015, ertb=0.001,
           step_hi=0.25, step_lo=0.1, roff=0, vmode=0, kon=0, d0=-0.10, d1=-0.20, kfl=0.25, reb_every=0)

def run(m, L, recon=False, **kw):
    """m: market dict with (P,T) arrays r, rf, rb, cpn, idxup, bondup. L: (P,T) pre-brake target exposure. -> (out, EE)"""
    p = dict(DEF); p.update(kw)
    f = lambda a, dt=np.float64: np.ascontiguousarray(a, dtype=dt)
    return runP(f(m['r']), f(m['rf']), f(m['rb']), f(m['cpn']), f(m['idxup'], np.bool_), f(m['bondup'], np.bool_), f(L),
                int(p['delay']), p['cost'], p['tax'], p['D'], int(p['harvest']), p['hthr'], p['cspr'], p['er3'], p['erq'], p['erb'],
                p['ertb'], p['step_hi'], p['step_lo'], int(p['roff']), int(p['vmode']), int(p['kon']), p['d0'], p['d1'], p['kfl'],
                int(p['reb_every']), 1 if recon else 0)

def stats(out, T):
    yrs = (T - WARM) / 252
    cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    return cg, out[:, 1]
