"""OV1-B engine: copy of beng.run1 (MS1 F1 engine, research/c3_brake/code/beng.py) with an overnight/intraday split.
mode 0 : v1 exactly (all fills at the close; ON ignored).
mode 1 : executed exposure DECREASES fill at the OPEN of the next day (see PRECOMMIT.md section 4):
         open: v0 *= 1 + 3 on_t ; pending decrease filled (v1 cost model) ; tax-payment sale (v1: previous close) ;
         intraday: v0 *= (1 + 3r - 2rf - er3/252) / (1 + 3 on_t), cash *= deposit factor ;
         close: increases / first day / decreases due on k % 252 == 251 / last path day fill at the close as v1,
         other decreases become pending. E at a pending close = the equity the v1 close fill would leave (cost accrued).
xcost : report-only stress, extra cost per side on every postponed fill (incl. TQQQ part of the postponed tax sale).
Event log (logev = 1, single path): rows [t_fill_open, dexp (index units), kind (1 level decrease, 2 tax sale), eligible]
  for every executed decrease of the run (mode 0: what v1 did; eligible = 1 if mode 1 would postpone it)."""
import numpy as np
from numba import njit, prange
WARM = 300
NOUT = 16


@njit(cache=False)
def run1s(r, rf, on, B, feat, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, out, rec, recon, fstep,
          mode, xcost, ev, evn, logev):
    T = r.shape[0]
    v0 = 0.0; v3 = 0.0; b0 = 0.0
    real = 0.0; due = 0.0
    held = 0.0; cur = -99.0
    q = np.zeros(delay + 1)
    st = np.zeros(32)
    kpk = 1.0; gpk = 1.0; emin = 1.0; mdd = 0.0; E = 1.0
    ntr = 0.0; taxp = 0.0; costp = 0.0
    E5 = np.nan; E7 = np.nan; E10 = np.nan; E12 = np.nan
    levsum = 0.0; bind = 0.0; nk = 0.0; trapd = 0.0; trun = 0.0; tmax = 0.0
    pend = False; pwant = 0.0; npost = 0.0; ntaxo = 0.0
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                due = tax * max(real - D, 0.0); real = 0.0
                if mode == 0 and due > 0:
                    tot = v0 + v3; taxp += due
                    f = min(due / max(tot, 1e-300), 1.0)
                    if logev == 1 and cur > 0:
                        n = int(evn[0])
                        if n < ev.shape[0]:
                            ev[n, 0] = t; ev[n, 1] = cur * f; ev[n, 2] = 2; ev[n, 3] = 1; evn[0] = n + 1
                    real += f * (v0 - b0)
                    v0 *= (1 - f); v3 *= (1 - f); b0 *= (1 - f)
                    due = 0.0
            want = q[0]
            for j in range(delay - 1): q[j] = q[j + 1]
            if k > 0:
                if mode == 0:
                    v0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
                    v3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
                else:
                    o3 = 3.0 * on[t]
                    v0 *= (1.0 + o3)                                   # overnight leg (cash: 0)
                    if pend:                                           # postponed decrease, filled at the open
                        tot = v0 + v3
                        w0 = pwant / 3
                        t0 = w0 * tot; t3 = (1 - w0) * tot
                        d0 = t0 - v0
                        tc = cost * abs(d0); tcx = xcost * abs(d0)
                        costp += tc + tcx
                        if d0 < 0 and v0 > 0:
                            fr = min(-d0 / v0, 1.0); real += fr * (v0 - b0); b0 *= 1 - fr
                        if d0 > 0: b0 += d0
                        sc = (tot - tc - tcx) / max(tot, 1e-300)
                        v0 = t0 * sc; v3 = t3 * sc
                        cur = pwant; ntr += 1; npost += 1
                        pend = False
                    if due > 0:                                        # tax-payment sale at the open
                        tot = v0 + v3; taxp += due
                        f = min(due / max(tot, 1e-300), 1.0)
                        if logev == 1 and cur > 0:
                            n = int(evn[0])
                            if n < ev.shape[0]:
                                ev[n, 0] = t; ev[n, 1] = cur * f; ev[n, 2] = 2; ev[n, 3] = 1; evn[0] = n + 1
                        real += f * (v0 - b0)
                        xs = xcost * f * v0
                        v0 *= (1 - f); v3 *= (1 - f); b0 *= (1 - f)
                        v3 -= xs; costp += xs
                        due = 0.0; ntaxo += 1
                    v0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252) / (1.0 + o3)   # intraday leg
                    v3 *= (1 + max(rf[t] - cspr / 252, 0.0) * (1 - 0.154))
            Ev = -1.0
            if want != cur:
                elig = k > 0 and want < cur and (k % 252 != 251) and (t < T - 1)
                if logev == 1 and k > 0 and want < cur:
                    n = int(evn[0])
                    if n < ev.shape[0]:
                        ev[n, 0] = t + 1; ev[n, 1] = cur - want; ev[n, 2] = 1; ev[n, 3] = 1.0 if elig else 0.0; evn[0] = n + 1
                if mode == 1 and elig:
                    pend = True; pwant = want
                    tot = v0 + v3                                      # equity the v1 close fill would leave
                    w0 = want / 3
                    t0 = w0 * tot; t3 = (1 - w0) * tot
                    d0 = t0 - v0
                    tc = cost * abs(d0)
                    sc = (tot - tc) / max(tot, 1e-300)
                    Ev = t0 * sc + t3 * sc
                else:
                    tot = v0 + v3
                    if k == 0:
                        tot = 1.0; v3 = 1.0
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
            if Ev >= 0.0:
                E = Ev
            else:
                E = v0 + v3
            gpk = max(gpk, E); emin = min(emin, E); mdd = min(mdd, E / gpk - 1)
            if k == 5 * 252 - 1: E5 = E
            if k == 7 * 252 - 1: E7 = E
            if k == 10 * 252 - 1: E10 = E
            if k == 12 * 252 - 1: E12 = E
            levsum += cur if cur > 0 else 0.0; nk += 1
            kpk = max(kpk, E)
            if cur <= 0 and E <= 0.25 * kpk:
                trapd += 1; trun += 1
                if trun > tmax: tmax = trun
            else:
                trun = 0.0
        b = B[t]
        if np.isnan(b): b = 0.0
        tg = bfn(t - WARM, E, kpk, b, held, feat[t], st, bp)
        if np.isnan(tg): tg = 0.0
        if tg > 3.0: tg = 3.0
        if tg < 0.0: tg = 0.0
        if t >= WARM and tg < b - 1e-9: bind += 1
        stp = step if (tg >= 1.0 or held >= 1.0) else fstep
        if abs(tg - held) >= stp or (tg == 0 and held > 0):
            held = np.round(tg / stp) * stp
        if t == WARM - 1:
            for j in range(delay): q[j] = held
        elif t >= WARM:
            q[delay - 1] = held
        if recon == 1 and t >= WARM:
            rec[t - WARM, 0] = E; rec[t - WARM, 1] = cur; rec[t - WARM, 2] = tg; rec[t - WARM, 3] = b
    unr = v0 - b0
    fin = E - due - tax * max(real + unr - D, 0.0)
    out[0] = fin; out[1] = emin; out[2] = mdd; out[3] = E7; out[4] = E12; out[5] = ntr; out[6] = taxp; out[7] = costp
    out[8] = E; out[9] = levsum / max(nk, 1.0); out[10] = bind / max(nk, 1.0); out[11] = npost; out[12] = ntaxo; out[13] = real
    out[14] = trapd / max(nk, 1.0); out[15] = tmax


@njit(parallel=True, cache=False)
def runPS(R, RF, ON, B, FEAT, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep, mode, xcost):
    P, T = R.shape; out = np.zeros((P, NOUT)); EE = np.zeros((P, T - WARM))
    for i in prange(P):
        rec = np.zeros((T - WARM, 4)); ev = np.zeros((1, 4)); evn = np.zeros(1)
        run1s(R[i], RF[i], ON[i], B[i], FEAT[i], delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, out[i], rec, 1,
              fstep, mode, xcost, ev, evn, 0)
        EE[i] = rec[:, 0]
    return out, EE


@njit(cache=False)
def run_log(r, rf, on, B, feat, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep, mode, xcost):
    T = r.shape[0]; out = np.zeros(NOUT); rec = np.zeros((T - WARM, 4)); ev = np.zeros((20000, 4)); evn = np.zeros(1)
    run1s(r, rf, on, B, feat, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, out, rec, 1, fstep, mode, xcost,
          ev, evn, 1)
    return out, rec, ev[:int(evn[0])]


def _pp(fstep):
    import beng
    k = dict(beng.F1); k['fstep'] = fstep; return beng._args(k)


def engine_s(c, B, bfn, bp, fstep, ON, mode=1, xcost=0.0):
    """same signature/return as std.engine (per-path cagr, equity curves) plus the split input ON (P, T) and mode."""
    import bk
    pp, D = _pp(fstep)
    o, EE = runPS(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(ON, dtype=np.float64),
                  np.ascontiguousarray(B, dtype=np.float64), np.ascontiguousarray(bk.features(c)), int(pp['delay']), pp['cost'],
                  pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], bfn,
                  np.asarray(bp, dtype=np.float64), float(pp['fstep']), int(mode), float(xcost))
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE, o


def engine_log(c, B, bfn, bp, fstep, ON, mode=0, xcost=0.0, i=0):
    """single path i with daily record and decrease event log."""
    import bk
    pp, D = _pp(fstep)
    F = np.ascontiguousarray(bk.features(c)[i])
    return run_log(np.ascontiguousarray(c.r[i]), np.ascontiguousarray(c.rf[i]), np.ascontiguousarray(ON[i], dtype=np.float64),
                   np.ascontiguousarray(B[i], dtype=np.float64), F, int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']),
                   pp['hthr'], pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']),
                   int(mode), float(xcost))
