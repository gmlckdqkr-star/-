"""MC1 W1 measurement core. Uses the locked MS1 std.py (contexts/engine/row/hold) unchanged; keeps per-path values so that
paired deltas vs ANY base candidate (not only s0.85) can be computed. <=2014 data only (std.contexts)."""
import os, sys, json, numpy as np
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import bk, ce, rx
from numba import njit
sys.path.insert(0, '/mnt/project-files/research/c3_brake/code/agents/alt'); sys.path.insert(0, '/mnt/project-files/research/c3_brake/code/agents/escape'); sys.path.insert(0, '/mnt/project-files/research/c3_brake/code/agents/cushion')
from alt import alt, AX
from esc import UN
from cush2 import NAMES as CN
CM, ov, S = bk._co()
ID = std.ident; Z = np.zeros(1)
AV23 = ce.AV23.copy()
PN = list(CN) + list(UN) + list(AX)       # 97 names; note kd1 appears twice (cush2 kd1 unused 9.0, ux kd1 .45)
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']

def av(**mods):
    """AV23 vector with named overrides; names resolved in order cush2 -> ux -> alt (first match)."""
    p = AV23.copy()
    for n, v in mods.items():
        i = PN.index(n); p[i] = float(v)
    return p
CUSH_OFF = dict(F=1e-9, F7=0.0, m=100.0)

# ---------------------------------------------------------------- brakes
@njit(cache=True)
def w1b(k, E, pk, b, held, x, st, p):
    """p[0] = mode in no-warning episodes, p[1] = mode in warned episodes, p[2:] = alt params.
    mode 0 = alt (AV23 logic) as is, 1 = raw (return b), 2 = crash budget only, 3 = crash budget + anti-stuck re-entry.
    alt is always called first so that its state (warning memory st[25], crash memory st[13], episode min st[28]) updates."""
    L = alt(k, E, pk, b, held, x, st, p[2:])
    nowarn = st[25] < 0.5
    md = p[0] if nowarn else p[1]
    if md < 0.5:
        return L
    if md < 1.5 or k < 0:
        return b
    e = E / pk
    gst = max(0.2, max(2.0 * (x[1] - 0.25), 2.0 * st[13]))
    Lg = max(1.0 - 0.2 / e, 0.0) / gst
    L2 = min(b, Lg)
    if md > 2.5 and st[28] < 0.2 and x[0] > 0.5:
        L2 = max(L2, min(0.5, b))
    return L2

@njit(cache=True)
def w1t(k, E, pk, b, held, x, st, p):
    """tax-day adjusted brake input. p[0] = 1 adjust on / 0 off, p[1] = shrink s (1 = AV23, .85 = s0.85), p[2:] = AV23.
    On the yearly tax day (k>0, k%252==0) the engine sells a fraction for tax; we estimate that fraction from the
    observed equity ratio vs the expected one (level held x index day return, rf ~ 0) and divide it out of the equity the
    brake sees (st[16] cumulative factor). Only when the index is not at a new high (x11<0 so its day return is exact)."""
    s = p[1]
    if k < 0:
        st[15] = 1.0; st[16] = 1.0; st[18] = 1.0; st[17] = x[11]; st[19] = held
        return alt(k, E, pk, b, held, x, st, p[2:])
    if p[0] > 0.5 and k > 0 and k % 252 == 0 and x[11] < 0.0 and st[15] > 0.0:
        r = (1.0 + x[11]) / (1.0 + st[17]) - 1.0
        lv = st[19]
        g = 1.0 + lv / 3.0 * (3.0 * r - 0.0245 / 252.0)
        tau = 1.0 - (E / st[15]) / g
        tau = min(max(tau, 0.0), 0.3)
        st[16] *= (1.0 - tau)
    st[15] = E; st[17] = x[11]; st[19] = held
    if p[0] > 0.5:
        Ea = E / st[16]
        if Ea > st[18]:
            st[18] = Ea
        pka = st[18]
    else:
        Ea = E; pka = pk
    Ev = pka * (1.0 - s * (1.0 - Ea / pka))
    return alt(k, Ev, pka, b, held, x, st, p[2:])

# ---------------------------------------------------------------- signals (same constructors as raw_core/code/ablate.py)
def c3(c): return bk.C3sig(c)
def volsw(c): v = c.vol(20); return np.where(v > 0.40, 1.0, 3.0)
def gate(c, B): off = ov.trend_gate(c, 200, 0.02, ov.macro_cond(c, ('inv', 'shock6m'))); return np.where(off, 0.0, B)
def caut(c, B): return np.where(ov.macro_cond(c, ('shock6m',)), np.minimum(B, 1.0), B)
def tq(c): return np.full(c.r.shape, 3.0)
def macro(c): return gate(c, caut(c, tq(c)))
SIG = dict(c3=c3, volsw=volsw, macro=macro)
B85 = rx.P_av23s(.85)

# ---------------------------------------------------------------- run / stats
_SIGC = {}
def sig(name, c, bn, shift=0):
    key = (name, bn, shift)
    if key not in _SIGC:
        B = SIG[name](c)
        if shift: B = np.roll(B, shift, axis=1)
        _SIGC[key] = np.ascontiguousarray(B, dtype=np.float64)
    return _SIGC[key]

def run(spec, keepE=False, bases=BASES):
    """spec(c, bn) -> (B, bfn, bp, fstep, kw). returns {bn: dict(fin=cagr per path, mdd=per-path mdd, E=curves?)}"""
    out = {}
    C = std.contexts()
    for bn in bases:
        c = C[bn]; B, bfn, bp, fs, kw = spec(c, bn)
        fin, EE = std.engine(c, B, bfn, bp, fs, **kw)
        d = dict(fin=fin, mdd=ce.mdd(EE), yrs=EE.shape[1] / 252)
        if keepE: d['E'] = EE
        out[bn] = d
    return out

_HOLD = {}
def holds():
    if _HOLD: return _HOLD
    C = std.contexts()
    for bn in BASES:
        c = C[bn]
        q, _ = std.hold(c, 1); l, _ = std.hold(c, 2); t, _ = std.engine(c, np.full(c.r.shape, 3.0), ID, Z, 0.5)
        _HOLD[bn] = dict(hold1x=float(np.median(q)), hold2x=float(np.median(l)), hold3x=float(np.median(t)))
    return _HOLD

def stats(R, refs):
    """R: run output; refs: {label: run output} -> per-basis dict with cagr, mdd, p10, dd80, dd95, d_<label>, pw_<label>"""
    o = {}
    for bn, d in R.items():
        f = d['fin']; m = d['mdd']
        s = dict(cagr=float(np.median(f)), mdd=float(np.median(m)))
        if len(f) > 1: s.update(p10=float(np.percentile(f, 10)), dd80=float(np.mean(m <= -0.8)), dd95=float(np.mean(m <= -0.95)))
        for lab, Rf in refs.items():
            dd = f - Rf[bn]['fin']
            s['d_' + lab] = float(np.median(dd)); s['pw_' + lab] = float(np.mean(dd > 1e-5))
        o[bn] = s
    return o

# ---------------------------------------------------------------- sub-accounts (H2)
def mix(RA, RB, x, rebal=False, ttax=True, cost=0.003, tax=0.22):
    """x of capital in account A, 1-x in account B (independent engines, own tax lots).
    rebal=False: final = x*FA + (1-x)*FB exactly (each account liquidated with its own final tax).
    rebal=True : every 252 days (after each account's own yearly tax) move money to restore x/(1-x); transferred amount pays
                 cost on both sides; ttax=True taxes 22% of the seller's gain vs its basis (basis = last rebalance value,
                 i.e. gains already taxed inside the account can be taxed again; no loss offset) -> conservative.
                 Account unit returns are taken from its own curve (its brake reads its own unit value, as a fund).
                 Final: each account value x its own liquidation factor F/E_last."""
    out = {}
    for bn in RA:
        A = RA[bn]; B = RB[bn]; yrs = A['yrs']
        FA = (1 + A['fin']) ** yrs; FB = (1 + B['fin']) ** yrs
        EA = np.maximum(A['E'], 1e-12); EB = np.maximum(B['E'], 1e-12)
        if not rebal:
            fin = x * FA + (1 - x) * FB; W = x * EA + (1 - x) * EB
        else:
            P, T = EA.shape
            lfA = FA / EA[:, -1]; lfB = FB / EB[:, -1]
            VA = x * EA[:, 0]; VB = (1 - x) * EB[:, 0]; bA = VA.copy(); bB = VB.copy()
            W = np.zeros((P, T)); W[:, 0] = VA + VB
            for t in range(1, T):
                VA = VA * EA[:, t] / EA[:, t - 1]; VB = VB * EB[:, t] / EB[:, t - 1]
                if t % 252 == 0:
                    tot = VA + VB; dA = x * tot - VA          # >0: move from B to A
                    mv = np.abs(dA)
                    sellA = dA < 0
                    fs = np.where(sellA, mv / np.maximum(VA, 1e-300), mv / np.maximum(VB, 1e-300))
                    gain = np.where(sellA, fs * (VA - bA), fs * (VB - bB))
                    tx = tax * np.maximum(gain, 0.0) if ttax else 0.0
                    net = mv - 2 * cost * mv - tx
                    VA = np.where(sellA, VA - mv, VA + net); VB = np.where(sellA, VB + net, VB - mv)
                    bA = np.where(sellA, bA * (1 - fs), bA + net); bB = np.where(sellA, bB + net, bB * (1 - fs))
                W[:, t] = VA + VB
            fin = VA * lfA + VB * lfB
        out[bn] = dict(fin=np.maximum(fin, 1e-9) ** (1 / yrs) - 1, mdd=ce.mdd(W), yrs=yrs)
    return out

def line(name, s, base_lab):
    p = s['dev250_path']
    return ('%-34s path %5.2f%% dd80 %3.0f%% p10 %5.2f | d_%s %+5.2f (pw %3.0f%%) d_s085 %+5.2f (pw %3.0f%%) | glued %5.2f | realNDX %5.2f (d %+5.2f) SPX55 %5.2f (d %+5.2f) SPX70 %5.2f (d %+5.2f)' % (
        name, 100 * p['cagr'], 100 * p.get('dd80', np.nan), 100 * p.get('p10', np.nan), base_lab, 100 * p['d_' + base_lab], 100 * p['pw_' + base_lab],
        100 * p['d_s085'], 100 * p['pw_s085'], 100 * s['dev250_glued']['cagr'],
        100 * s['real_ndx_86_14']['cagr'], 100 * s['real_ndx_86_14']['d_' + base_lab],
        100 * s['real_spx_55_85']['cagr'], 100 * s['real_spx_55_85']['d_' + base_lab],
        100 * s['real_spx_70_85']['cagr'], 100 * s['real_spx_70_85']['d_' + base_lab]))

def verdict(s, base_lab, base_stats):
    """PRECOMMIT_MC1 sec.2 W1 rules vs one base candidate."""
    p = s['dev250_path']; bp = base_stats['dev250_path']
    real_ok = all(s[b]['d_' + base_lab] >= -0.005 for b in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'))
    imp = p['d_' + base_lab] >= 0.01 and p['pw_' + base_lab] >= 0.60 and real_ok and p['dd80'] <= bp['dd80'] + 1e-12
    par = p['d_' + base_lab] >= -0.003 and p['dd80'] <= bp['dd80'] - 0.20 and real_ok
    return dict(improve=bool(imp), pareto=bool(par), real_ok=bool(real_ok))
