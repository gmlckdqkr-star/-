"""COPY of research/wx1/m1/code/m1_engine.py for KL1; only change: trade cost is an argument (KR ETF 0.15%, US 0.3%)."""
"""M1 screening engine (numba). After-cost PRE-TAX daily log growth of a rule vs always-1x, MS1 cost conventions:
products  3x: 3r-2rf-2.45%/252, 2x: 2r-rf-2.45%/252, 1x: r-0.2%/252, cash: max(rf-2%/252,0)*(1-15.4%), -1x: -r+2rf-2.45%/252
trade     decision at close t -> traded at close t+2 (position earning day i = decision of close i-3, as beng/ms1eng);
          cost 0.3% x traded notional of non-cash legs (A->B both non-cash = 0.6%, A->cash or cash->A = 0.3%),
          applied at the close of the trade day after that day's return (ms1eng order).
rule      boolean expression over <=3 atoms (int8 1/0/-1); any atom unknown -> rule inactive -> holds 1x (= benchmark).
shape     (on, off) leverage; min-hold m: after an on/off switch the new state is kept >= m decision days.
Product codes: 0 = 3x, 1 = 2x, 2 = 1x, 3 = cash, 4 = -1x."""
import numpy as np
from numba import njit, prange

SHAPES = ((3, 0), (3, 1), (2, 0), (1, 0), (3, -1), (2, -1), (1, -1))
LEV2CODE = {3: 0, 2: 1, 1: 2, 0: 3, -1: 4}
SHAPE_CODES = np.array([[LEV2CODE[a], LEV2CODE[b]] for a, b in SHAPES], np.int64)
HOLDS = (1, 5, 21)
NONCASH = np.array([1, 1, 1, 0, 1], np.int64)
COST = 0.003


def products(r, rf):
    r = np.asarray(r, float); rf = np.asarray(rf, float)
    X = np.empty((5, len(r)))
    X[0] = 3 * r - 2 * rf - 0.0245 / 252
    X[1] = 2 * r - rf - 0.0245 / 252
    X[2] = r - 0.002 / 252
    X[3] = np.maximum(rf - 0.02 / 252, 0.0) * (1 - 0.154)
    X[4] = -r + 2 * rf - 0.0245 / 252
    return np.ascontiguousarray(X)


@njit(cache=True)
def rule_value(A, a1, a2, a3, st, t):
    """1 / 0 / -1 (unknown) of the rule expression at day t."""
    v1 = A[a1, t]
    if v1 < 0:
        return -1
    if st == 0:
        return v1
    v2 = A[a2, t]
    if v2 < 0:
        return -1
    if st == 1:
        return 1 if (v1 == 1 and v2 == 1) else 0
    if st == 2:
        return 1 if (v1 == 1 or v2 == 1) else 0
    v3 = A[a3, t]
    if v3 < 0:
        return -1
    if st == 3:
        return 1 if (v1 == 1 and v2 == 1 and v3 == 1) else 0
    if st == 4:
        return 1 if (v1 == 1 or v2 == 1 or v3 == 1) else 0
    if st == 5:
        return 1 if ((v1 == 1 and v2 == 1) or v3 == 1) else 0
    if st == 6:
        return 1 if ((v1 == 1 or v2 == 1) and v3 == 1) else 0
    return -1


@njit(cache=True)
def decisions(A, a1, a2, a3, st, pon, poff, hold, t1, dec, act):
    """dec[t] = decided product code at close t (min-hold applied), act[t] = rule active (all atoms known).
    Inactive -> 1x at once; leaving the inactive state is immediate; an on/off switch needs the current state to have
    been held >= hold decision days."""
    held = 2; age = 1 << 30; prev = 0
    for t in range(t1):
        v = rule_value(A, a1, a2, a3, st, t)
        if v < 0:
            act[t] = 0
            if held != 2:
                held = 2; age = 0
            else:
                age += 1
            prev = 0
        else:
            act[t] = 1
            want = pon if v == 1 else poff
            if want != held:
                if prev == 0 or age + 1 >= hold:
                    held = want; age = 0
                else:
                    age += 1
            else:
                age += 1
            prev = 1
        dec[t] = held


@njit(cache=True)
def path_logdiff(X, dec, t1, g, cost):
    """g[i] = log growth of the rule on day i minus log growth of 1x on day i (both after cost; 1x never trades)."""
    for i in range(t1):
        p = dec[i - 3] if i >= 3 else 2
        x = X[p, i]
        lg = np.log1p(x)
        pn = dec[i - 2] if i >= 2 else 2           # position for day i+1 = decision of close i-2
        if i + 1 < t1 and pn != p:
            c = cost * (NONCASH[p] + NONCASH[pn])
            lg += np.log1p(-c)
        g[i] = lg - np.log1p(X[2, i])


@njit(parallel=True, cache=True)
def screen(A, X, rules, t1, mon, nmon, w0, w1, out_m, out_s, cost):
    """rules: (N, 7) int64 [a1, a2, a3, struct, shape_on_code, shape_off_code, hold].
    mon[i] = month slot of day i (-1 outside the windows); w0..w1 = window day range for stats.
    out_m (N, nmon) float32 monthly sums of g; out_s (N, 4): sum g in window, active days in window, switches, days."""
    N = rules.shape[0]
    for k in prange(N):
        dec = np.empty(t1, np.int64); act = np.zeros(t1, np.int8); g = np.zeros(t1)
        a1, a2, a3, st, pon, poff, hold = rules[k, 0], rules[k, 1], rules[k, 2], rules[k, 3], rules[k, 4], rules[k, 5], rules[k, 6]
        decisions(A, a1, a2, a3, st, pon, poff, hold, t1, dec, act)
        path_logdiff(X, dec, t1, g, cost)
        s = 0.0; na = 0.0; sw = 0.0
        for i in range(w0, w1):
            m = mon[i]
            if m >= 0:
                out_m[k, m] += g[i]
            s += g[i]
            if i >= 3 and act[i - 3] == 1:
                na += 1
            if dec[i] != dec[i - 1]:
                sw += 1
        out_s[k, 0] = s; out_s[k, 1] = na; out_s[k, 2] = sw; out_s[k, 3] = w1 - w0


@njit(cache=True)
def one_path(A, X, rule, t1, cost):
    """daily detail of one rule: dec, act, g (for confirmation / MS1 / parity)."""
    dec = np.empty(t1, np.int64); act = np.zeros(t1, np.int8); g = np.zeros(t1)
    decisions(A, rule[0], rule[1], rule[2], rule[3], rule[4], rule[5], rule[6], t1, dec, act)
    path_logdiff(X, dec, t1, g, cost)
    return dec, act, g


@njit(cache=True)
def equity_from_dec(X, dec, t0, t1, cost):
    """pre-tax after-cost equity of a decision sequence, account opened all cash and buying at close t0 (ms1eng k = 0
    convention: both delay slots hold the decision of close t0-1, no return on day t0)."""
    E = np.empty(t1 - t0)
    q0 = dec[t0 - 1]; q1 = dec[t0 - 1]
    cur = -1; v = 1.0
    for t in range(t0, t1):
        want = q0; q0 = q1
        if t > t0:
            v *= 1 + X[cur, t]
        if want != cur:
            if t == t0:
                c = cost * NONCASH[want]
            else:
                c = cost * (NONCASH[cur] + NONCASH[want])
            v *= 1 - c
            cur = want
        E[t - t0] = v
        q1 = dec[t]
    return E
