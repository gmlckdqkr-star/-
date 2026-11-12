"""v1 weak-state edits (FCR, PGC) and volatility-information rules (IVV, PRX-SOXL, PRX-QLD).

NOTES (every reading choice)
General
 - v1 OFF state := (xv1.ref(v)['B'] == 0). In v1, B is 0 only through the trend gate (the vol cap and the caution cap give 1, never 0).
 - "ungated level" := 3, or 1 where vol20 > 0.40 (NaN vol counts as not above) or the shock6m caution flag is on (v1's own C3 caps).
 - S (shock6m caution flag) := v.c.F['shock6m'][0]; vol20 := v.c.vol(20)[0] (NaN where it does not exist).
 - A level is changed by editing a copy of B; bfn, bp, fstep stay v1's. Rows with a NaN needed input keep v1's B / weight 0.
FCR (fast-crash floor)
 - Episode start g: OFF[g] and not OFF[g-1] (row 0 never starts an episode). H = max of index level over rows g-251..g (252 rows);
   it needs 252 rows, else the episode is SLOW (never happens after the 300 warm-up rows). h = LAST row in the window with
   level == H (most recent tie). a = g - h. FAST iff a <= A.
 - FAST and OFF: level 1.0. The episode ends at the first row where v1 is not OFF. A new OFF episode is judged anew.
 - P3 demotion: if level < (1 - D) * H on any row from g on (row g included) of a FAST episode, level 0 for the rest of the episode.
 - P4 upgrade: state U, switched on at a row t >= g + 10 where level > SMA50, off where level < 0.97 * SMA50, otherwise unchanged
   (hysteresis, U = off at g); while U the base level is the ungated level, else the 1.0 floor. SMA50 = v.c.sma(50)[0].
PGC (post-gain cut)
 - G_t = level[t] / level[t - n] - 1 with n = 63 (P5: n = 126). A cut starts at t if G_t >= g, no cut is active (t > last row of the
   current cut) and t - (last row of the previous cut) >= 63 (the 63 is fixed, also for P5). The cut covers rows t..t+K-1;
   level is min(v1 base level, c) there. c = 2 gives base level 2.
IVV (equity-IV veto of the shock6m cap)
 - A_t = mean of VIX closes v[t-20..t] (21 closes, NaN if any is missing). D1: raw = A_t < k * A_{t-126}; D2: raw = A_t < mean(v[t-251..t]).
   raw is False wherever an input is NaN. Z = cm.debounce(raw, 5): starts 0 (raw[0] False), flips after 5 equal consecutive raw closes.
 - B' = 3 where Z and S and vol20 <= 0.40 and v1's B == 1 (the cap is what holds B at 1 there; B == 0 rows stay 0, B == 3 rows stay 3);
   B' = B elsewhere. Controls N1, N2a, N2b are not implemented (the text says they are not candidates).
PRX (panic resolved)
 - VIX = v.c.vix[0]. m_t = median of v[t-503..t] (504 closes, NaN if any missing -> inactive). P_t = max(v[t-62..t]) (63 closes);
   tau_t = the row of the most recent maximum in that window. PANIC = P >= a * m. RES = PANIC and max(v[t-4..t]) <= 0.60 * P_t.
 - ENTRY at row t (decision at the close of t, engine delays): needs RES, no open position, tau_t > row of last exit (before any exit: allowed).
   Exits are tested on rows after the entry row only. The weight is W on rows entry..exit-1 and 0 on the exit row onwards.
 - P_entry = P_t of the entry row; X_entry = level of the entry row.
 - A missing VIX close makes m / P (and so the rule) NaN = inactive for every row whose window holds it; an open position is then kept
   (the VIX exit cannot fire on a NaN close). The VIX has no missing close from its first close to the end of the <= 2014 calendar.
PRX-SOXL
 - X = cm.semis_level(v) (Chips until SOXX exists, SOXX after; the 'semis' input). dd_s = X_s / max(X[s-503..s]) - 1 (504-row window,
   shorter at the very start of the array). SEMI_t = min(dd[t-62..t]) <= -D.
 - Instrument: cm.fund(v, 'SOXL', semis 1x return, 3).
 - carry = 0 (mode 0): inc = 1 (tranche). "weight = min(W, idle cash)", "target = drifted weight (no rebalancing)" and "the harness cuts
   it whenever v1 needs the cash" are exactly the engine's tranche rule in mode 0: one buy of W (cut to the idle cash) when the entry
   comes into force, then the position drifts, is cut pro rata when v1 needs the money and is never topped up or bought back.
   With inc = 0 the engine would re-set the sleeve to W at every change of v1's level (that is rebalancing, and a buy-back after a cut).
   Price of this choice: the engine ignores bands with inc = 1, so "capped at 0.40 of equity" is NOT enforced for carry = 0 (open point).
 - carry = 1: mode 1 for the whole candidate (a candidate has one mode); the weight is 0 outside the open sleeve so mode only acts
   while open. inc = 0 without re-set flags: in mode 1 the engine lets the weight drift between entry and exit. "capped at 0.40 of
   equity": engine skim band up = 0.40 / W - 1 (the engine then cuts the position back to W, it cannot cut to 0.40 exactly). E5 not used.
 - E3: the 'above 1.02 * SMA200(X)' flag is set from the entry row on (entry row close included), exit at the first later row with X < 0.98 * SMA200(X).
 - E4: exit on the row where t - t_entry >= 756. E2: v_t >= 0.85 * P_entry. E1: X_t <= 0.75 * X_entry.
 - E5 (carry = 0 only): the harness cut is engine state, a candidate cannot see it. Proxy: the sleeve is zero when v1 leaves no idle cash,
   i.e. v.ref_held[t] >= 3 (v1 alone actually holds everything in the 3x fund on row t). It is tested from row t_entry + 2 on: the entry
   decided at the close of t_entry is in force two rows later (the engine's delay), there is no sleeve the harness could cut before
   that. Exit on the first such row. NOT exact (open point): v1's level inside the candidate account can differ from v1 alone.
   The proxy only ends the episode (a new VIX peak can then open a new one); the engine itself never buys back after a cut (inc = 1).
PRX-QLD
 - ENTRY also needs v1 B_t == 0. Exits: X1 B_t > 0 (v1's own B, on rows after entry), X2 v_t >= 0.85 * P_entry, X3 t - t_entry >= 126.
 - Instrument cm.fund(v, 'QLD', v.c.r[0], 2); mode 0; inc = 0; "held at constant target W" = Wt = W constant while open, no re-set flags
   or bands: the engine re-sets the position to W only when v1's level changes and lets it drift otherwise (no daily rebalancing).
 - 'a' is the panic multiple (1.75 or 2.00) in PANIC = P >= a * m.
 - The modelled 2x fund before QLD exists is cbase's (yearly drag 0.0095 + 0.0075 = 0.0170, as CANDIDATE_API.md states).
   cbase is used as instructed; the difference is a shared-helper question, not a choice of this rule.
T0 (in states.configs.json)
 - FCR, PGC: none (index inputs only, look-backs inside the 300 warm-up rows).
 - IVV: the row of the 147th VIX close (D1: first row on which A_t and A_{t-126} both exist) / of the 252nd VIX close (D2). The veto Z
   starts at 0 and needs 5 closes, so the first row on which the rule can differ from v1 is 4 rows after T0.
 - PRX-SOXL, PRX-QLD: the row of the 504th VIX close (first m_t). The semiconductor series and both fund models exist from the first row.
"""
import numpy as np
import xv1
import cbase as cm

NAMES_SOXL = ('ret:SOXL', 'semis')
NAMES_QLD = ('ret:QLD',)


# ---------------------------------------------------------------------------------------------- v1 pieces
def _vol20(v): return np.asarray(v.c.vol(20)[0], dtype=np.float64)


def _ungated(v):
    vol = _vol20(v); S = np.asarray(v.c.F['shock6m'][0], dtype=bool)
    return np.where(S | (vol > 0.40), 1.0, 3.0)


# ---------------------------------------------------------------------------------------------- weak states
def fast_crash_floor(v, A=30, D=None, upgrade=False):
    """FCR: in a FAST OFF episode hold level 1.0 instead of 0 (see NOTES). A = max rows since the 252-row high; D demotion depth; upgrade = SMA50 rule."""
    o = xv1.ref(v); B = o['B'].copy(); B0 = o['B']; off = B0 == 0
    lvl = cm.ndx_level(v); s50 = np.asarray(v.c.sma(50)[0], dtype=np.float64); ung = _ungated(v)
    fast = False; H = np.nan; g = -1; demoted = False; U = False
    for t in range(v.T):
        if not off[t]:
            fast = False; continue
        if t > 0 and not off[t - 1]:                       # first row of an OFF episode
            fast = False; demoted = False; U = False
            if t >= 251 and not np.isnan(lvl[t - 251:t + 1]).any():
                w = lvl[t - 251:t + 1]; H = w.max(); h = 251 - int(np.argmax(w[::-1])); a = 251 - h
                fast = a <= A; g = t
        if not fast or np.isnan(lvl[t]): continue
        if D is not None and lvl[t] < (1 - D) * H: demoted = True
        if demoted: B[t] = 0.0; continue
        if upgrade and t >= g + 10 and not np.isnan(s50[t]):
            if U and lvl[t] < 0.97 * s50[t]: U = False
            elif (not U) and lvl[t] > s50[t]: U = True
        B[t] = ung[t] if (upgrade and U) else 1.0
    o['B'] = B
    return o


def post_gain_cut(v, g=0.30, c=1.0, K=21, n=63):
    """PGC: when the n-row index return >= g (and no cut active, 63 rows since the last cut ended) cap the level at c for K decision rows."""
    o = xv1.ref(v); B = o['B'].copy(); lvl = cm.ndx_level(v); G = lvl / cm.lag(lvl, n) - 1
    cut_end = -10 ** 9; last_end = -10 ** 9
    for t in range(v.T):
        if t > cut_end and not np.isnan(G[t]) and G[t] >= g and t - last_end >= 63:
            cut_end = t + K - 1; last_end = cut_end
        if t <= cut_end: B[t] = min(B[t], c)
    o['B'] = B
    return o


# ---------------------------------------------------------------------------------------------- volatility information
def iv_veto(v, mode='D1', k=1.0):
    """IVV: lift v1's shock6m 1x cap (back to 3) while the equity-IV veto Z is on."""
    o = xv1.ref(v); B0 = o['B']; vix = np.asarray(v.c.vix[0], dtype=np.float64)
    A = cm.sma(vix, 21)
    if mode == 'D1': ref = k * cm.lag(A, 126)
    elif mode == 'D2': ref = cm.sma(vix, 252)
    else: raise ValueError(mode)
    ok = ~np.isnan(A) & ~np.isnan(ref)
    raw = ok & (np.where(ok, A, 0.0) < np.where(ok, ref, 0.0))
    Z = cm.debounce(raw, 5)
    S = np.asarray(v.c.F['shock6m'][0], dtype=bool); vol = _vol20(v)
    lift = Z & S & (vol <= 0.40) & (B0 == 1)
    o['B'] = np.where(lift, 3.0, B0)
    return o


def _panic(v, a):
    """m (504-close median), P (63-close max), tau (row of the latest max), RES flag; NaN / False where inputs are missing"""
    vix = np.asarray(v.c.vix[0], dtype=np.float64); T = v.T
    m = np.full(T, np.nan); P = np.full(T, np.nan); tau = np.full(T, -1); res = np.zeros(T, dtype=bool)
    for t in range(T):
        if t >= 503:
            w = vix[t - 503:t + 1]
            if not np.isnan(w).any(): m[t] = np.median(w)
        if t >= 62:
            w = vix[t - 62:t + 1]
            if not np.isnan(w).any(): P[t] = w.max(); tau[t] = t - int(np.argmax(w[::-1]))
        if t >= 4 and not np.isnan(m[t]) and not np.isnan(P[t]):
            w5 = vix[t - 4:t + 1]
            res[t] = (P[t] >= a * m[t]) and (not np.isnan(w5).any()) and bool((w5 <= 0.60 * P[t]).all())
    return vix, m, P, tau, res


def panic_soxl(v, D=0.30, W=0.15, carry=0):
    """PRX-SOXL: SOXL sleeve after a resolved VIX panic while semiconductors are deeply down (idle cash, or mode 1 with carry)."""
    o = xv1.ref(v); T = v.T; r1 = np.asarray(v.x['semis'], dtype=np.float64)
    vix, m, P, tau, res = _panic(v, 1.75)
    X = cm.semis_level(v); mx = cm.roll_max(X, 504); dd = X / mx - 1; ddmin = cm.roll_min(dd, 63)
    semi = ~np.isnan(ddmin) & (np.where(np.isnan(ddmin), 0.0, ddmin) <= -D)
    s200 = cm.sma(X, 200); held = np.asarray(v.ref_held, dtype=np.float64) if carry == 0 else None
    Wt = np.zeros(T); is_open = False; last_exit = -1; te = 0; Xe = Pe = 0.0; above = False
    for t in range(T):
        if is_open:
            x = X[t]; ex = False
            if above and not np.isnan(s200[t]) and x < 0.98 * s200[t]: ex = True
            if not np.isnan(x) and x <= 0.75 * Xe: ex = True
            if not np.isnan(vix[t]) and vix[t] >= 0.85 * Pe: ex = True
            if t - te >= 756: ex = True
            if carry == 0 and t - te >= 2 and held[t] >= 3.0 - 1e-9: ex = True     # E5 proxy, only once the entry is in force
            if not ex and not np.isnan(s200[t]) and x > 1.02 * s200[t]: above = True
            if ex: is_open = False; last_exit = t
            else: Wt[t] = W
        if (not is_open) and res[t] and semi[t] and tau[t] > last_exit and not np.isnan(X[t]):
            is_open = True; te = t; Xe = X[t]; Pe = P[t]; Wt[t] = W
            above = (not np.isnan(s200[t])) and X[t] > 1.02 * s200[t]
    g = cm.fund(v, 'SOXL', r1, 3)
    if carry: o.update(G=g[:, None], Wt=Wt[:, None], mode=1, inc=0, RB=np.zeros((T, 1)), up=np.array([0.40 / W - 1.0]))
    else: o.update(G=g[:, None], Wt=Wt[:, None], mode=0, inc=1, RB=np.zeros((T, 1)))      # tranche: one buy, drift, cut by the engine, no buy-back
    return o


def panic_qld(v, a=1.75, W=0.33):
    """PRX-QLD: QLD idle-cash position from a resolved VIX panic while v1 is in its OFF state, handed back when v1's gate turns on."""
    o = xv1.ref(v); T = v.T; B = o['B']
    vix, m, P, tau, res = _panic(v, a)
    Wt = np.zeros(T); is_open = False; last_exit = -1; te = 0; Pe = 0.0
    for t in range(T):
        if is_open:
            ex = B[t] > 0 or (not np.isnan(vix[t]) and vix[t] >= 0.85 * Pe) or (t - te >= 126)
            if ex: is_open = False; last_exit = t
            else: Wt[t] = W
        if (not is_open) and res[t] and B[t] == 0 and tau[t] > last_exit:
            is_open = True; te = t; Pe = P[t]; Wt[t] = W
    g = cm.fund(v, 'QLD', v.c.r[0], 2)
    o.update(G=g[:, None], Wt=Wt[:, None], mode=0, inc=0, RB=np.zeros((T, 1)))
    return o
