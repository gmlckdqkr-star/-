# AC3: three walled accounts (종합 Z / ISA I / 선물 F) all following one s0.85 level series. MS1 conditions. <=2014 only.
# See ../PRECOMMIT_AC3.md. Units: total start wealth = 1.0 = W KRW.
import sys, os, json, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/acct3/nbcache')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, rx, bk, beng
from numba import njit, prange

WARM = beng.WARM

@njit(parallel=True, cache=False)
def levels(R, RF, B, FEAT, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep):
    """reference s0.85 book: executed level per day (P, T-WARM) and its after-tax final value"""
    P, T = R.shape; L = np.zeros((P, T - WARM)); fin = np.zeros(P)
    for i in prange(P):
        rec = np.zeros((T - WARM, 4)); out = np.zeros(beng.NOUT)
        beng.run1(R[i], RF[i], B[i], FEAT[i], delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, out, rec, 1, fstep)
        L[i] = rec[:, 1]; fin[i] = out[0]
    return L, fin

@njit(cache=False)
def joint(r, rf, L, LI, W, wZ, wI, wF, rule, imode, Nc0, ccost, ctax, harvest, hthr, cspr, er3, icost, ier, im, mm, fcost, out, Erec):
    n_days = L.shape[0]
    D = 2.5e6 / W; capY = 2e7 / W; capT = 1e8 / W; ifree = 2e6 / W
    # initial deposits
    I0 = min(wI, capY); pend = wI - I0
    z0 = 0.0; z3 = wZ + pend; zb = 0.0; zreal = 0.0; curZ = -99.0
    i0 = 0.0; i3 = I0; ib = 0.0; ireal = 0.0; icon = I0; ytd = I0; curI = -99.0
    ef = wF; n = 0.0; nc = Nc0; freal = 0.0; curF = -99.0
    fpk = max(ef, 1e-12); fmdd = 0.0; fneg = 0.0; fliq = 0.0; fmaxlev = 0.0; fdead = 0.0
    gpk = 1.0; mdd = 0.0; E7 = np.nan; E12 = np.nan; E = 1.0
    for k in range(n_days):
        t = k + WARM
        if k > 0 and k % 252 == 0:
            # --- taxes (Z exactly as MS1 run1)
            due = ctax * max(zreal - D, 0.0); zreal = 0.0
            if due > 0:
                tot = z0 + z3; f = min(due / max(tot, 1e-300), 1.0)
                zreal += f * (z0 - zb); z0 *= (1 - f); z3 *= (1 - f); zb *= (1 - f)
            if imode == 1:
                due = 0.099 * max(ireal, 0.0); ireal = 0.0
                if due > 0:
                    tot = i0 + i3; f = min(due / max(tot, 1e-300), 1.0)
                    ireal += f * (i0 - ib); i0 *= (1 - f); i3 *= (1 - f); ib *= (1 - f)
            due = 0.11 * max(freal - D, 0.0); freal = 0.0
            if due > 0: ef -= min(due, ef)
            # --- flows between accounts (once a year)
            ytd = 0.0
            EZ = z0 + z3; EI = i0 + i3; Etot = EZ + EI + ef
            aI = 0.0; aZ = 0.0; aF = 0.0   # net inflow to each account
            room = min(capY - ytd, capT - icon)
            if rule == 0:
                aI = min(pend, room, EZ); pend -= aI; aZ = -aI
            else:
                aI = min(max(wI * Etot - EI, 0.0), room, EZ + ef)
                rest = Etot - EI - aI
                if wZ + wF > 0:
                    tZ = rest * wZ / (wZ + wF); tF = rest - tZ
                else:
                    tZ = rest; tF = 0.0
                aZ = tZ - EZ; aF = tF - ef
            if aI > 0: icon += aI; ytd += aI; i3 += aI; curI = -99.0
            if aF != 0: ef += aF; freal += 0.0; curF = -99.0
            if aZ < 0:
                out_amt = -aZ
                take = min(out_amt, z3); z3 -= take; rem = out_amt - take
                if rem > 0 and z0 > 0:
                    fr = min(rem / z0, 1.0); zreal += fr * (z0 - zb); zb *= 1 - fr; z0 *= 1 - fr
                curZ = -99.0
            elif aZ > 0:
                z3 += aZ; curZ = -99.0
        if k > 0:
            z0 *= (1 + 3 * r[t] - 2 * rf[t] - er3 / 252)
            cr = max(rf[t] - cspr / 252, 0.0) * (1 - 0.154)
            z3 *= (1 + cr)
            i0 *= (1 + 2 * r[t] - rf[t] - ier / 252)
            i3 *= (1 + cr)
            pnl = n * nc * (r[t] - rf[t]); ef += pnl; freal += pnl; nc *= (1 + r[t])
            if n > 0 and ef < n * nc * mm:
                nn = np.floor(max(ef, 0.0) / (nc * im)); c = (n - nn) * nc * fcost
                ef -= c; freal -= c; n = nn; fliq += 1
            if ef < 0:
                fneg += 1; ef = 0.0; n = 0.0
        # --- Z trades (MS1 run1 logic)
        want = L[k]
        if want != curZ:
            tot = z0 + z3
            w0 = want / 3; t0 = w0 * tot; t3 = (1 - w0) * tot; d0 = t0 - z0; tc = ccost * abs(d0)
            if d0 < 0 and z0 > 0:
                fr = min(-d0 / z0, 1.0); zreal += fr * (z0 - zb); zb *= 1 - fr
            if d0 > 0: zb += d0
            sc = (tot - tc) / max(tot, 1e-300); z0 = t0 * sc; z3 = t3 * sc; curZ = want
        if harvest > 0 and k % 252 == 251 and z0 > 1e-12:
            target = D - zreal; U = z0 - zb; f = 0.0
            if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
            if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
            rz = f * U; sv = f * z0
            if sv > 0 and ctax * abs(rz) > hthr * 2 * ccost * sv:
                tc = 2 * ccost * sv; zreal += rz; zb = zb - (sv - rz) + (sv - tc); z0 -= tc
        # --- ISA trades (2x product, weight L/3)
        wantI = LI[k]
        if wantI != curI:
            tot = i0 + i3
            w0 = wantI / 3; t0 = w0 * tot; t3 = (1 - w0) * tot; d0 = t0 - i0; tc = icost * abs(d0)
            if d0 < 0 and i0 > 0:
                fr = min(-d0 / i0, 1.0); ireal += fr * (i0 - ib); ib *= 1 - fr
            if d0 > 0: ib += d0
            sc = (tot - tc) / max(tot, 1e-300); i0 = t0 * sc; i3 = t3 * sc; curI = wantI
        # --- futures trades: on level change, quarterly roll, or after a flow
        roll = (k > 0 and k % 63 == 0)
        drift = False
        if ef > 1e-12 and n * nc / ef > want + 0.5: drift = True   # A1: cut when leverage drifts >0.5x above target
        if want != curF or roll or drift:
            nt = np.floor(want * ef / nc + 0.5)
            mx = min(np.floor(ef / (nc * im)), np.floor((want + 0.5) * ef / nc))   # A1: never above target+0.5x
            if nt > mx: nt = mx
            if nt < 0: nt = 0.0
            keep = min(nt, n)
            c = abs(nt - n) * nc * fcost
            if roll: c += 2 * keep * nc * fcost
            ef -= c; freal -= c; n = nt; curF = want
        if ef > 1e-12:
            lv = n * nc / ef
            if lv > fmaxlev: fmaxlev = lv
        fpk = max(fpk, ef)
        if fpk > 1e-12: fmdd = min(fmdd, ef / fpk - 1)
        E = z0 + z3 + i0 + i3 + ef
        gpk = max(gpk, E); mdd = min(mdd, E / gpk - 1)
        if k == 7 * 252 - 1: E7 = E
        if k == 12 * 252 - 1: E12 = E
        Erec[k] = E
    finZ = z0 + z3 - ctax * max(zreal + (z0 - zb) - D, 0.0)
    if imode == 1: finI = i0 + i3 - 0.099 * max(ireal + (i0 - ib), 0.0)
    else: finI = i0 + i3 - 0.099 * max(i0 + i3 - icon - ifree, 0.0)
    finF = ef - 0.11 * max(freal - D, 0.0)
    out[0] = finZ + finI + finF; out[1] = mdd; out[2] = E7; out[3] = E12
    out[4] = fmdd; out[5] = fneg; out[6] = fliq; out[7] = fmaxlev
    out[8] = finZ; out[9] = finI; out[10] = finF; out[11] = icon

@njit(parallel=True, cache=False)
def jointP(R, RF, L, LI, W, wZ, wI, wF, rule, imode, Nc0, ccost, ctax, harvest, hthr, cspr, er3, icost, ier, im, mm, fcost):
    P = R.shape[0]; nd = L.shape[1]; out = np.zeros((P, 12)); EE = np.zeros((P, nd))
    for i in prange(P):
        joint(R[i], RF[i], L[i], LI[i], W, wZ, wI, wF, rule, imode, Nc0, ccost, ctax, harvest, hthr, cspr, er3, icost, ier, im, mm, fcost,
              out[i], EE[i])
    return out, EE

PP, _ = beng._args(dict(beng.F1, fstep=0.1))
# A2 (amendment, before selection): ISA brake on its own account equity, as breakthrough/m4 (true 2x product, scale 2/3)
_src = open(beng.__file__).read()
_a = _src.index('@njit(cache=True)\ndef run1('); _b = _src.index('@njit(parallel=True, cache=True)\ndef runP(')
_body = _src[_a:_b].replace('@njit(cache=True)', '@njit(cache=False)')
assert _body.count('3 * r[t] - 2 * rf[t]') == 1 and _body.count('w0 = want / 3') == 1
_body = _body.replace('3 * r[t] - 2 * rf[t]', '2.0 * r[t] - 1.0 * rf[t]').replace('w0 = want / 3', 'w0 = want / 2.0').replace('def run1(', 'def run1x(')
_g = dict(np=np, njit=njit, WARM=WARM, NOUT=beng.NOUT); exec(_body, _g); run1x = _g['run1x']
@njit(cache=False)
def av23sL(k, E, pk, b, held, x, st, p):
    s = p[0]
    return rx.av23s(k, E, pk, b, held / s, x, st, p[1:]) * s
bp23 = np.concatenate([np.array([2 / 3]), rx.P_av23s(.85)])
@njit(parallel=True, cache=False)
def levels2(R, RF, B, FEAT, delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, fstep):
    P, T = R.shape; L = np.zeros((P, T - WARM)); fin = np.zeros(P)
    for i in prange(P):
        rec = np.zeros((T - WARM, 4)); out = np.zeros(beng.NOUT)
        run1x(R[i], RF[i], B[i], FEAT[i], delay, cost, tax, D, harvest, hthr, cspr, er3, step, bfn, bp, out, rec, 1, fstep)
        L[i] = rec[:, 1]; fin[i] = out[0]
    return L, fin
BASES = None
def prep():
    """per basis: R, RF, reference levels L (Z/F delay 2) and LI (ISA delay 3), and MS1 s0.85 per-path fin"""
    global BASES
    if BASES is not None: return BASES
    BASES = {}
    for bn, c in std.contexts().items():
        R = np.ascontiguousarray(c.r); RF = np.ascontiguousarray(c.rf)
        B = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
        L, fin = levels(R, RF, B, feat, int(PP['delay']), PP['cost'], PP['tax'], 0.25, int(PP['harvest']), PP['hthr'], PP['cspr'],
                        PP['er3'], PP['step'], rx.av23s, rx.P_av23s(.85), 0.1)
        LI = np.concatenate([L[:, :1], L[:, :-1]], axis=1)
        L2, _ = levels2(R, RF, B, feat, 3, 0.003, 0.099, 0.0, 0, PP['hthr'], PP['cspr'], PP['er3'], PP['step'], av23sL, bp23, 0.1)
        BASES[bn] = dict(R=R, RF=RF, L=np.ascontiguousarray(L), LI=np.ascontiguousarray(LI), LIown=np.ascontiguousarray(L2 * 1.5), ref=fin)
    return BASES

DEF = dict(W=1e7, rule=1, imode=1, Nc0=7e7, ccost=0.003, ctax=0.22, icost=0.003, ier=0.0095 + 0.015, im=0.08, mm=0.073,
           fcost=0.00021)

def run(bn, wZ, wI, wF, **kw):
    p = dict(DEF); p.update(kw); b = prep()[bn]
    o, EE = jointP(b['R'], b['RF'], b['L'], b['LIown'] if p.get('isa_own', 1) else b['LI'], float(p['W']), wZ, wI, wF, int(p['rule']), int(p['imode']), p['Nc0'] / p['W'],
                   p['ccost'], p['ctax'], int(PP['harvest']), PP['hthr'], PP['cspr'], PP['er3'], p['icost'], p['ier'], p['im'], p['mm'],
                   p['fcost'])
    yrs = EE.shape[1] / 252
    cg = np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1
    ref = np.maximum(b['ref'], 1e-9) ** (1 / yrs) - 1
    m = o[:, 1]
    r = dict(cagr=float(np.median(cg)), mdd=float(np.median(m)), w7=float(np.median(o[:, 2])), w12=float(np.median(o[:, 3])))
    if o.shape[0] > 1:
        r.update(p10=float(np.percentile(cg, 10)), dd80=float(np.mean(m <= -0.8)), dd95=float(np.mean(m <= -0.95)))
    r.update(d_vs_s085=float(np.median(cg - ref)), pw=float(np.mean(cg > ref + 1e-5)), ref_s085=float(np.median(ref)))
    if wF > 0:
        r.update(F_dd80=float(np.mean(o[:, 4] <= -0.8)), F_negpaths=int(np.sum(o[:, 5] > 0)), F_liq_med=float(np.median(o[:, 6])),
                 F_maxlev_med=float(np.median(o[:, 7])), F_maxlev_max=float(np.max(o[:, 7])))
    return r, cg
