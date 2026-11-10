"""NTILT engine (ONF1): v1 exactly as MS1 (beng.run1 / mfeng mode 0: TQQQ + cash, 22% tax) plus a night-only MNQ position
("tilt") entered at the US close and closed at the next US open.  <=2014 pools only (MS1 contexts).

impl 0 : v1 in the stock account (TQQQ + cash) + separate futures account F that only carries the night tilt.
         F is funded with phi of total equity, swept back to phi once a year (after taxes); stock-side sales realise gains.
         v1's brake sees the stock sleeve as a unit value (flows do not count as performance).  tau=0, phi=0 == std.engine.
impl 1 : everything in one futures account (MF1 mode 1, daily re-fit) + tilt.  tau=0 == mfeng mode 1.
Tilt: notional Y = min(tau, vc/sigma^2) * total equity at close t (gate by v1 level), capped by margin F/(mi*mm) - X,
      P&L next day = Y*(night return - 0.8132*(rf + s/252)), fee per side `fee` at entry and exit, futures tax taxf yearly
      on net futures P&L minus D, no carry-forward.  Night return ron[t] = close(t-1)->open(t) of path day t (ms1f split).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
for p in (paths.PROJ + '/research/measure_std', paths.PROJ + '/research/c3_brake/code'):
    if p not in sys.path: sys.path.insert(0, p)
import numpy as np, pandas as pd
from numba import njit, prange
import std, beng, bk, ov
import ms1f
WARM = beng.WARM; NO = 24; WON = 0.8132


@njit(cache=True)
def run1N(r, rf, ron, sg, B, feat, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
          impl, tau, gate, vc, phi, s, fee, feeb, taxf, cmode, N0, mi, mm, L3x, m, out, rec):
    T = r.shape[0]
    v0 = 0.0; v3 = 0.0; b0 = 0.0
    F = 0.0; X = 0.0; Y = 0.0; Nn = N0
    real = 0.0; realF = 0.0; due = 0.0
    held = 0.0; cur = -99.0
    q = np.zeros(delay + 1); st = np.zeros(32)
    kpk = 1.0; gpk = 1.0; emin = 1.0; mdd = 0.0; E = 1.0; EU = 1.0; scale = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0; E7 = np.nan; E12 = np.nan
    tiltpl = 0.0; tiltdays = 0.0; nliq = 0.0; neg = 0.0; dead = False; ysum = 0.0; nk = 0.0; fneg = 0.0; tcost = 0.0
    if impl == 1: F = 1.0
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            # ---------------- yearly taxes (+ sweep of the futures account, impl 0)
            if k > 0 and k % 252 == 0:
                if impl == 0:
                    due = tax * max(real - D, 0.0); real = 0.0
                    if due > 0:
                        tot = v0 + v3; taxp += due
                        f = min(due / max(tot, 1e-300), 1.0)
                        real += f * (v0 - b0)
                        v0 *= (1 - f); v3 *= (1 - f); b0 *= (1 - f)
                        due = 0.0
                dF = taxf * max(realF - D, 0.0); realF = 0.0
                if dF > 0:
                    F -= dF; taxp += dF
                if impl == 0 and phi > 0:
                    ES = v0 + v3; d = phi * (ES + F) - F
                    if d > 0 and ES > 0:                       # stock -> futures account
                        d = min(d, ES)
                        x = min(d, v3); v3 -= x; y = d - x; tc = 0.0
                        if y > 0 and v0 > 0:
                            y = min(y, v0); fr = y / v0
                            real += fr * (v0 - b0); b0 *= 1 - fr; v0 -= y
                            tc = cost * y; costp += tc
                        F += x + y - tc
                        scale *= (ES - x - y) / ES
                    elif d < 0 and ES > 0:                     # futures account -> stock (same TQQQ/cash weights)
                        a = -d; w0 = v0 / ES
                        buy = a * w0; tc = cost * buy; costp += tc
                        v0 += buy - tc; b0 += buy - tc; v3 += a - buy; F -= a
                        scale *= (ES + a) / ES
            want = q[0]
            for j in range(delay - 1): q[j] = q[j + 1]
            # ---------------- night tilt P&L (Y set at the previous close, closed at today's open)
            if k > 0 and Y > 0:
                x = Y * (ron[t] - WON * (rf[t] + s / 252)); tc = fee * Y * (1 + ron[t])
                F += x - tc; realF += x - tc; costp += tc; tcost += tc; tiltpl += x - tc; Y = 0.0
                if F <= 0: fneg = 1.0
            if impl == 0:
                if k > 0:
                    v0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
                    v3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
                    if cmode == 2 and F > 0: F += F * 0.007 / 252 * (1 - 0.154)
                    Nn *= (1 + r[t])
                if want != cur:
                    tot = v0 + v3
                    if k == 0:
                        tot = 1.0 - phi; v3 = tot; F = phi; scale = 1.0 - phi
                    w0 = want / 3
                    t0 = w0 * tot; t3 = (1 - w0) * tot
                    d0 = t0 - v0
                    tc = cost * abs(d0)
                    costp += tc
                    if d0 < 0 and v0 > 0:
                        fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                    if d0 > 0: b0 += d0
                    sc = (tot - tc) / max(tot, 1e-300)
                    v0 = t0 * sc; v3 = t3 * sc
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
                ES = v0 + v3; EU = ES / scale; E = ES + F
            else:
                if k > 0 and not dead:
                    pl = X * (r[t] - rf[t] - s / 252)
                    F += pl; realF += pl
                    if cmode == 1:
                        F += F * max(rf[t] - 0.02 / 252, 0.0) * (1 - 0.154)
                    elif cmode == 2:
                        F += F * 0.007 / 252 * (1 - 0.154)
                    X *= (1 + r[t]); Nn *= (1 + r[t])
                    if X > 0 and k % 63 == 0:
                        tc = 2 * feeb * X; F -= tc; realF -= tc; costp += tc
                    if F <= 0:
                        neg = 1.0; dead = True; F = 1e-9; X = 0.0
                    elif X > 0 and F < m * X:
                        tc = 0.01 * X; F -= tc; realF -= tc; X = 0.0; nliq += 1; cur = -99.0
                        if F <= 0:
                            neg = 1.0; dead = True; F = 1e-9
                if want != cur and not dead:
                    Lx = L3x if want >= 3.0 - 1e-9 else want
                    if N0 > 0:
                        Xn = np.round(Lx * F / Nn) * Nn
                    else:
                        Xn = Lx * F
                    tc = feeb * abs(Xn - X)
                    F -= tc; realF -= tc; costp += tc
                    if Xn != X: ntr += 1
                    X = Xn; cur = want
                elif not dead and cur > 0:
                    Lx = L3x if cur >= 3.0 - 1e-9 else cur
                    if N0 > 0:
                        Xn = np.round(Lx * F / Nn) * Nn; go = abs(Xn - X) > 0.5 * Nn
                    else:
                        Xn = Lx * F; go = abs(Xn - X) > 0.05 * Xn
                    if go:
                        tc = feeb * abs(Xn - X); F -= tc; realF -= tc; costp += tc; X = Xn; ntr += 1
                EU = F; E = F
            # ---------------- size tonight's tilt (info: close t, vol lagged by `delay`)
            if tau > 0 and (not dead) and F > 0 and t < T - 1:
                g = 1.0
                if gate == 1 and cur > 0: g = 0.0
                if gate == 2 and cur <= 0: g = 0.0
                Lt = tau
                sv_ = sg[t - delay]
                if vc > 0 and sv_ > 0: Lt = min(tau, vc / (sv_ * sv_))
                Yt = g * Lt * E
                cap = F / (mi * mm) - X
                if Yt > cap: Yt = max(cap, 0.0)
                if N0 > 0: Yt = math.floor(Yt / Nn + 1e-9) * Nn
                if Yt > 0:
                    tc = fee * Yt; F -= tc; realF -= tc; costp += tc; tcost += tc; tiltpl -= tc; Y = Yt; tiltdays += 1
                    ysum += Yt / E
            gpk = max(gpk, E); emin = min(emin, E); mdd = min(mdd, E / gpk - 1)
            if k == 7 * 252 - 1: E7 = E
            if k == 12 * 252 - 1: E12 = E
            nk += 1
            kpk = max(kpk, EU)
            rec[k] = E
        b = B[t]
        if np.isnan(b): b = 0.0
        tg = bfn(t - WARM, EU, kpk, b, held, feat[t], st, bp)
        if np.isnan(tg): tg = 0.0
        if tg > 3.0: tg = 3.0
        if tg < 0.0: tg = 0.0
        stp = step if (tg >= 1.0 or held >= 1.0) else fstep
        if abs(tg - held) >= stp or (tg == 0 and held > 0):
            held = np.round(tg / stp) * stp
        if t == WARM - 1:
            for j in range(delay): q[j] = held
        elif t >= WARM:
            q[delay - 1] = held
    if impl == 0:
        unr = v0 - b0
        fin = (v0 + v3) - due - tax * max(real + unr - D, 0.0) + F - taxf * max(realF - D, 0.0)
    else:
        fin = F - taxf * max(realF - D, 0.0)
    out[0] = fin; out[1] = emin; out[2] = mdd; out[3] = E7; out[4] = E12; out[5] = ntr; out[6] = taxp; out[7] = costp
    out[8] = E; out[9] = tiltpl; out[10] = tiltdays / max(nk, 1.0); out[11] = neg; out[12] = nliq; out[13] = fneg
    out[14] = ysum / max(nk, 1.0); out[15] = tcost


@njit(parallel=True, cache=True)
def runPN(R, RF, RON, SG, B, FEAT, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
          impl, tau, gate, vc, phi, s, fee, feeb, taxf, cmode, N0, mi, mm, L3x, m):
    P, T = R.shape; out = np.zeros((P, NO)); EE = np.zeros((P, T - WARM))
    for i in prange(P):
        run1N(R[i], RF[i], RON[i], SG[i], B[i], FEAT[i], delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep,
              impl, tau, gate, vc, phi, s, fee, feeb, taxf, cmode, N0, mi, mm, L3x, m, out[i], EE[i])
    return out, EE


_C = {}
def prep(bn, mode):
    """night simple returns and lagged-vol arrays on the path grid of basis bn."""
    key = (bn, mode, ms1f.SPLIT['seed'], ms1f.SPLIT['demean'], ms1f.SPLIT['cut_m'], ms1f.SPLIT['carry'])
    if key in _C: return _C[key]
    Bs = ms1f.bases()[bn]; ii = Bs['ii']; c = Bs['ctx']
    on_p, id_p = ms1f.split_on_path(bn, mode)
    assert np.allclose(np.exp(on_p + id_p)[:, 1:] - 1, c.r[:, 1:], atol=1e-9)      # night + day = close-to-close (col 0 is zeroed by ov.Ctx)
    ron = np.ascontiguousarray(np.exp(on_p) - 1)
    if ('sg', bn) not in _C:
        lr = np.log1p(c.r); n = 20
        c1 = np.cumsum(np.c_[np.zeros(len(lr)), lr], axis=1); c2 = np.cumsum(np.c_[np.zeros(len(lr)), lr * lr], axis=1)
        mu = (c1[:, n:] - c1[:, :-n]) / n; v = ((c2[:, n:] - c2[:, :-n]) / n - mu * mu) * n / (n - 1)
        _C[('sg', bn)] = np.ascontiguousarray(np.c_[np.full((len(lr), n - 1), np.nan), np.sqrt(np.maximum(v, 0) * 252)])
        _C[('feat', bn)] = np.ascontiguousarray(bk.features(c))
    for k in [k for k in _C if len(k) == 6 and k[0] == bn]: del _C[k]                     # keep one night array per basis
    _C[key] = ron
    return ron


def run(bn, mode='C', impl=0, tau=0.0, gate=0, vc=0.0, phi=0.0, s=0.004, fee=0.000083, feeb=0.0002, taxf=0.11, cmode=0,
        W0=1e7, notional=0.0, mi=0.075, mm=1.6, L3x=3.0, m=0.07):
    c = ms1f.bases()[bn]['ctx']; ron = prep(bn, mode)
    if ('s085', bn) not in _C: _C[('s085', bn)] = std.s085(c)
    B, bfn, bp, fstep = _C[('s085', bn)]
    k = dict(beng.F1); k['fstep'] = fstep; k['W0'] = W0; pp, D = beng._args(k)
    N0 = notional / W0 if notional > 0 else 0.0
    o, EE = runPN(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), ron, _C[('sg', bn)], np.ascontiguousarray(B, dtype=np.float64),
                  _C[('feat', bn)], int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'],
                  pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']),
                  impl, tau, gate, vc, phi, s, fee, feeb, taxf, cmode, N0, mi, mm, L3x, m)
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE, o


_REF = {}
def ref(bn, W0=1e7):
    if (bn, W0) not in _REF: _REF[(bn, W0)] = run(bn, 'C', 0, W0=W0)
    return _REF[(bn, W0)]


def summ(fin, EE, o, fr):
    r, _ = std.row(fin, EE); d = fin - fr
    r.update(d=float(np.median(d)), pw=float(np.mean(d > 1e-5)), tilt_on=float(np.median(o[:, 10])), avg_tilt=float(np.median(o[:, 14])),
             p_fneg=float(np.mean(o[:, 13] > 0)), p_neg=float(np.mean(o[:, 11] > 0)))
    return r


BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')
def measure(name, mode='C', bases_=BASES, verbose=True, **kw):
    out = {}
    for bn in bases_:
        fin, EE, o = run(bn, mode, **kw); fr = ref(bn, kw.get('W0', 1e7))[0]
        rr = summ(fin, EE, o, fr); out[bn] = rr
        if verbose:
            print('%-26s %-15s %s cagr %.4f d %+.4f pw %.2f mdd %.3f dd80 %.2f tilt_on %.2f avgY %.2f fneg %.3f' % (
                name, bn, mode, rr['cagr'], rr['d'], rr['pw'], rr['mdd'], rr.get('dd80', np.nan), rr['tilt_on'], rr['avg_tilt'], rr['p_fneg']), flush=True)
    return out


def parity():
    C = std.contexts()
    for bn in ('real_ndx_86_14', 'dev250_path'):
        c = C[bn]; fin, EE, o = run(bn, 'C', 0)
        B, bfn, bp, fs = std.s085(c); f2, E2 = std.engine(c, B, bfn, bp, fs)
        print(bn, 'nt impl0 tau0 med %.5f  std %.5f  maxabs fin %.2e  maxabs EE %.2e' % (np.median(fin), np.median(f2), np.max(np.abs(fin - f2)), np.max(np.abs(EE - E2))), flush=True)
    sys.path.insert(0, paths.PROJ + '/research/mf1/code')
    import mfeng
    for bn in ('real_ndx_86_14', 'dev250_path'):
        c = C[bn]; fin, EE, o = run(bn, 'C', 1, W0=1e8)
        B, bfn, bp, fstep = std.s085(c); k = dict(beng.F1); k['fstep'] = fstep; k['W0'] = 1e8; pp, D = beng._args(k)
        o2, E2 = mfeng.runPF(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64), _C[('feat', bn)],
                             int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'],
                             bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']), 1, 3.0, 0.0, 0, 0.004, 0.0002, 0.07, 0.11, 1)
        f2 = np.maximum(o2[:, 0], 1e-9) ** (1 / (E2.shape[1] / 252)) - 1
        print(bn, 'nt impl1 tau0 med %.5f  mfeng mode1 %.5f  maxabs fin %.2e' % (np.median(fin), np.median(f2), np.max(np.abs(fin - f2))), flush=True)


if __name__ == '__main__':
    parity()
