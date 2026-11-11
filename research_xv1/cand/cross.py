"""Cross-asset rules, idle-cash fills and the midterm calendar add. Five candidates (functions): sbc_cap, chip_lead, tmf_fill,
soxl_sleeve, midterm_add.

NOTES (reading choices)
 General
  G1. 756-row look-backs (3-year highs) use the history available in the view (the calendar starts about 300 rows before the
      account, 1984; the semiconductor series itself goes back to 1926 but only the view rows are readable): before 756 rows
      exist the window is the available history (same choice as bridge.py). So T0 = None for every configuration.
  G2. "v1's level after the brake" at the decision close t: v.ref_target[t] (for 'final level is 3', rounded to v1's order grid
      o['fstep'] = 0.1, so 2.96 counts as 3). Where the text says "actually holds" (idle = 1 - q/3) v.ref_held[t] is used.
      v.ref_held / v.ref_target read 0 on the 300 warm-up rows (shadow account starts at the account start), so idle reads
      1.0 there; state machines that use idle may therefore enter on warm-up rows (the engine ignores weights on those rows
      but the state carries into the account). Observed: tmf_fill P4/P6 (no H) hold weight 1.0 on warm-up rows 0..299 and the
      weight is already 0 on the first account row; the other state machines have no weight on warm-up rows.
  G3. Stateful machines process a row in this order: ends / exits first (weight 0 on that row), then, only if flat at the
      start of the row, entry. No exit and re-entry on the same row.
  G4. Rows where a needed input is NaN: no entry, indicators False; the base level stays v1's and weight 0.
 1. sbc_cap (SBC-CAP, P1-P6)
  S1. q = log1p(NDX return), b = -(y10[t] - y10[t-1]) with y10 = v.m['y10'] (the yield series v1 itself uses, lagged one day by
      the chain; bond holidays are already repeated values, so a zero change is a valid pair). Pairs with a NaN are dropped.
  S2. rho = Pearson over the last N rows ending at t using the valid pairs in them. Minimum pairs = min(200, N): 200 for N=252
      and N=504 (as written), and N (full window) for N=126, because 200 pairs cannot exist in a 126-row window.
  S3. NEG: on when rho < -0.05, off when rho > +0.05, else unchanged; starts 0; NaN rho leaves it unchanged (cm.hyst).
  S4. Edit of v1's base level: base before caution = 1 where vol20 > 0.40 else 3 (L_on=3, vcap=0.40, vlev=1; NaN vol -> 3).
      v1 caution row = shock6m flag (v.c.F['shock6m'][0]). A row is 'released' when caution and NEG (and, in P5, chip
      confirmation) hold and v1's B is not 0 (B == 0 is the trend-and-macro gate, left alone, B before the gate is 1 or 3 so
      B == 0 identifies the gate exactly). On released rows B = min(base, Lr). Everything else is v1's B. bfn, bp, fstep as v1.
  S5. P5 chip confirmation: R = S / NDX where S = level of v.x['semis'] (Chips to SOXX splice) and NDX = v.c.lvl[0];
      confirmed when R > SMA200(R) (strict; NaN -> not confirmed -> cap stays).
  S6. P6 control: NEG treated as 1 on every row, Lr = 3 (cap removed everywhere the gate does not send v1 to cash).
 2. chip_lead (CHIP-LEAD-12M, points 1-6)
  C1. S = level of v.x['semis']; Q = v.c.lvl[0]; R = S/Q. DD_t = any u in [t-503, t] with S_u <= (1-D) * max(S[u-755..u]).
  C2. UP = cm.trend_flag(S, 200, 0.02) (starts off). LEAD: on when R > SMA200(R), off after 20 consecutive closes R < SMA200(R)
      (cm.hyst; starts off). Point 6 (lead=False): LEAD dropped from both entry and ending.
  C3. Entry needs DD, UP, LEAD, v1 final level 3 (G2) and no cooldown. Active: Wt[SOXL] = a on rows with final level 3, 0 on
      other rows. mode 1 (extras first) gives v1's 3x fund level/3 of the rest = (1-a) on level-3 rows. inc = 0.
  C4. Window ends at the first row t with: t - entry >= H (no cooldown after this end), UP off, LEAD off, S_t <= 0.8 * max(S
      since entry, row t included) (cooldown after these three). Cooldown 63 rows: blocked rows end+1..end+63, a new entry
      at end+64 earliest. Weight is 0 on the end row. SOXL = cm.fund(v, 'SOXL', semis, 3).
 3. tmf_fill (gated long-Treasury fill, P1-P6)
  T1. dy = y10[t] - y10[t-1] (v.m['y10']), r = NDX return; a day is valid when r != 0, dy != 0 and both finite; kappa = mean of
      sign(r)*sign(dy) over the last W VALID days (not the last W rows); NaN until W valid days exist. H on at kappa >= 0.10,
      off at kappa <= 0, else unchanged, 0 before kappa exists. S = shock6m flag. E = NDX level < SMA50 (NaN -> False).
  T2. idle = 1 - v.ref_held[t]/3 (G2); target = min(cap, floor(10 * idle + 1e-9)/10) when Gate, else 0.
  T3. Trade rule: the 'held' weight is the weight this candidate last set (its own state, not the drifted actual weight).
      New weight = target if |target - held| >= 0.20 (>= 0.2 - 1e-9) or (target == 0 and held > 0), else held. mode 0, inc 0.
  T4. Instruments: TMF = cm.fund(v, 'TMF', tlt1x, 3) with tlt1x = ret:TLT spliced with v.c.rb[0]. TLT vehicle (P3, P6) = actual
      ret:TLT where it exists, before it cm.lev(v.c.rb[0], rf, 1) (plain index fund, 0.2%/yr). The project's own pre-inception
      synthetic series of E06 is not readable, the rule-translation series (rb proxy) is used instead.
  T5. P4 / P6: H dropped. P5: E added. Reported-alongside variants (ungated, demeaned null) are not configurations.
 4. soxl_sleeve (S1-S6)
  L1. X = level of v.x['semis'] (SOXX / Chips splice). DD = X / max(X over last 756 rows) - 1 (G1). idle = 1 - ref_held/3.
  L2. FLAT -> LONG when DD <= -D, (confirm: X > SMA50(X); NaN -> False), idle >= 0.5, not blocked. LONG weight = min(w, idle)
      in BOTH modes (literal text; in mode 1 the sleeve therefore never exceeds v1's idle cash either, only the engine's
      priority rule differs and exit (g) is mode 0 only, exit (h) mode 1 only).
  L3. Exits (checked in this order): (e) X <= 0.85 * X(entry row) -> flat and block; (f) DD > -0.10; (g) mode 0: idle < 0.05
      on 5 consecutive closes (the count runs on all rows); (h) mode 1: X <= 0.75 * max X since entry (entry row included).
  L4. Block after a stop: confirm variant: the block lifts on the first row after the stop on which X > SMA50 after at least one
      row after the stop with X < SMA50 (entry possible that same row); no-confirm: blocked rows stop+1..stop+20.
  L5. SOXL = cm.fund(v, 'SOXL', semis, 3). Engine: mode 0 (S1-S4) or 1 (S5-S6), inc 0, no bands.
 5. midterm_add (MIDTERM-ADD, P1-P6)
  M1. Calendar only from v.x['cal:month','cal:dom','cal:dow','cal:ymod4'] of the decision row. The execution day (t+2 rows) is
      projected by two weekday steps (no holidays) from the row's own month/day/weekday/year-mod-4 with month lengths and
      leap years by rule (ymod4 == 0). Holidays do not fall near any window edge, so the projection equals the real row t+2
      at every edge. Window (P1): projected day in Oct-Dec with ymod4 == 2, or Jan-Jun with ymod4 == 3. P5: Jan-Apr.
      P3: from the first trading day after Election Day (Tuesday after the first Monday of November): projected day in
      November with day-of-month >= first_Monday + 2 (election Tuesday + 1), or December, in a year with ymod4 == 2.
  M2. C = 3 if vol20 <= 0.40 else 1 (v.c.vol(20)[0]; NaN -> 0) inside the window, P2: C = 3 always, else 0.
  M3. x = phi * max(0, C - L)/3 with L = v.ref_held[t] (G2, 'actually holds'). Trade rule: weight changes only when
      |x - held_weight| >= 1/6 (- 1e-9) or x == 0 with held > 0 (own last-set weight). mode 0, inc 0.
  M4. TQQQ = cm.fund(v, 'TQQQ', NDX return, 3); P6: QLD = cm.fund(v, 'QLD', NDX return, 2), same weight formula. The netting
      or re-label cost is an engine term and is not modelled.
"""
import numpy as np
import xv1
import cbase as cm


def _hy(on, off, start=False):
    return cm.hyst(on, off, start)


def _lt(a, b):
    with np.errstate(invalid='ignore'): return np.asarray(a < b)


def _gt(a, b):
    with np.errstate(invalid='ignore'): return np.asarray(a > b)


def _highs(lvl, n=756):
    H = cm.roll_max(lvl, n); ok = ~np.isnan(H) & ~np.isnan(lvl)
    return H, np.where(ok, lvl / np.where(ok, H, 1.0) - 1.0, np.nan)


def _dy(v):
    y = np.asarray(v.m['y10'], dtype=np.float64); d = np.full(v.T, np.nan); d[1:] = y[1:] - y[:-1]; return d


# ------------------------------------------------------------------------------------------------ 1. SBC-CAP
NAMES_SBC = ()
NAMES_SBC_CHIP = ('semis',)


def _roll_corr(x, y, n, minp):
    ok = ~(np.isnan(x) | np.isnan(y)); xv = np.where(ok, x, 0.0); yv = np.where(ok, y, 0.0)
    cs = lambda a: np.cumsum(np.r_[0.0, a])
    c0, cx, cy, cxy, cxx, cyy = cs(ok.astype(float)), cs(xv), cs(yv), cs(xv * yv), cs(xv * xv), cs(yv * yv)
    T = len(x); lo = np.maximum(np.arange(T) + 1 - n, 0); hi = np.arange(T) + 1
    d = lambda c: c[hi] - c[lo]
    m = d(c0); sx, sy, sxy, sxx, syy = d(cx), d(cy), d(cxy), d(cxx), d(cyy)
    num = m * sxy - sx * sy; den = (m * sxx - sx * sx) * (m * syy - sy * sy)
    out = np.full(T, np.nan); good = (m >= minp) & (den > 1e-18)
    out[good] = num[good] / np.sqrt(den[good]); return out


def _base_pre(v):
    """v1's base level before the caution cap and the gate: 1 where vol20 > 0.40 else 3"""
    return np.where(_gt(v.c.vol(20)[0], 0.40), 1.0, 3.0)


def sbc_cap(v, N=252, Lr=3.0, chip=False, always=False):
    o = xv1.ref(v); B = o['B'].copy()
    q = np.log1p(v.c.r[0]); b = -_dy(v)
    neg = np.ones(v.T, dtype=bool) if always else _hy(_lt(_roll_corr(q, b, N, min(200, N)), -0.05), _gt(_roll_corr(q, b, N, min(200, N)), 0.05))
    caution = np.asarray(v.c.F['shock6m'][0], dtype=bool)
    rel = caution & neg & (B != 0)
    if chip:
        R = cm.semis_level(v) / cm.ndx_level(v); rel &= _gt(R, cm.sma(R, 200))
    B[rel] = np.minimum(_base_pre(v)[rel], Lr)
    o['B'] = B; return o


# ------------------------------------------------------------------------------------------------ 2. CHIP-LEAD-12M
NAMES_CHIP = ('ret:SOXL', 'semis')


def chip_lead(v, D=0.40, a=1.0 / 3.0, H=252, lead=True, dd_win=504, hi_win=756, cool=63, stop=0.80):
    o = xv1.ref(v); T = v.T; S = cm.semis_level(v); Q = cm.ndx_level(v); g = cm.fund(v, 'SOXL', v.x['semis'], 3)
    Hmax = cm.roll_max(S, hi_win); f = _lt(S, (1 - D) * Hmax) | (S == (1 - D) * Hmax)
    c = np.r_[0, np.cumsum(f)]; idx = np.arange(T); DD = (c[idx + 1] - c[np.maximum(0, idx - dd_win + 1)]) > 0
    UP = cm.trend_flag(S, 200, 0.02)
    R = S / Q; sR = cm.sma(R, 200)
    LEAD = _hy(_gt(R, sR), cm.consec(_lt(R, sR)) >= 20) if lead else np.ones(T, dtype=bool)
    L3 = np.round(v.ref_target / o['fstep']) * o['fstep'] >= 3.0 - 1e-9
    W = np.zeros((T, 1)); act = False; ent = -1; pk = np.nan; blocked_to = -1
    for t in range(T):
        if act:
            why = None
            if not np.isnan(S[t]): pk = max(pk, S[t])
            if t - ent >= H: why = 'H'
            elif not UP[t]: why = 'UP'
            elif not LEAD[t]: why = 'LEAD'
            elif S[t] <= stop * pk: why = 'STOP'
            if why:
                act = False
                if why != 'H': blocked_to = t + cool
                continue
            W[t, 0] = a if L3[t] else 0.0
        elif t > blocked_to and DD[t] and UP[t] and LEAD[t] and L3[t] and not np.isnan(S[t]) and not np.isnan(g[t]):
            act = True; ent = t; pk = S[t]; W[t, 0] = a
    o.update(G=g[:, None], Wt=W, mode=1, inc=0, RB=np.zeros((T, 1))); return o


# ------------------------------------------------------------------------------------------------ 3. gated long-Treasury fill
def _kappa(r, dy, W):
    sg = np.sign(r) * np.sign(dy); valid = np.isfinite(sg) & (sg != 0) & (r != 0) & (dy != 0)
    k = np.cumsum(valid); cv = np.r_[0.0, np.cumsum(sg[valid])]
    out = np.full(len(r), np.nan); ok = k >= W
    out[ok] = (cv[k[ok]] - cv[k[ok] - W]) / W; return out


def _bond(v, veh):
    tlt1 = cm.spliced(v.x['ret:TLT'], v.c.rb[0])
    if veh == 'TMF': return cm.fund(v, 'TMF', tlt1, 3)
    if veh == 'TLT': return cm.spliced(v.x['ret:TLT'], cm.lev(v.c.rb[0], v.c.rf[0], 1))
    raise ValueError(veh)


def _trade(target, band, T):
    """own last-set weight; move only when |target - held| >= band or target == 0 and held > 0"""
    w = np.zeros(T); h = 0.0
    for t in range(T):
        x = target[t]
        if abs(x - h) >= band - 1e-9 or (x == 0 and h > 0): h = x
        w[t] = h
    return w


def tmf_fill(v, veh='TMF', cap=1.0, useH=True, useE=False, W=252):
    o = xv1.ref(v); T = v.T; g = _bond(v, veh)
    kap = _kappa(v.c.r[0], _dy(v), W)
    Hs = _hy(_gt(kap, 0.10) | (kap == 0.10), _lt(kap, 0.0) | (kap == 0.0)) if useH else np.ones(T, dtype=bool)
    gate = ~np.asarray(v.c.F['shock6m'][0], dtype=bool) & Hs
    if useE: gate &= _lt(v.c.lvl[0], v.c.sma(50)[0])
    idle = 1.0 - v.ref_held / 3.0
    tg = np.where(gate & ~np.isnan(g), np.minimum(cap, np.floor(10 * idle + 1e-9) / 10), 0.0)
    w = _trade(tg, 0.20, T)
    o.update(G=g[:, None], Wt=w[:, None], mode=0, inc=0, RB=np.zeros((T, 1))); return o


# ------------------------------------------------------------------------------------------------ 4. SOXL crash-rebound sleeve
def soxl_sleeve(v, D=0.35, confirm=True, mode=0, w=0.15):
    o = xv1.ref(v); T = v.T; g = cm.fund(v, 'SOXL', v.x['semis'], 3); X = cm.semis_level(v)
    _, dd = _highs(X); s50 = cm.sma(X, 50); above = _gt(X, s50); below = _lt(X, s50)
    idle = 1.0 - v.ref_held / 3.0; low5 = cm.consec(idle < 0.05)
    W = np.zeros((T, 1)); lg = False; blocked = False; seen = False; st_t = -1; ex = np.nan; pk = np.nan
    for t in range(T):
        if np.isnan(X[t]) or np.isnan(dd[t]) or np.isnan(g[t]): lg = False; continue
        if blocked:
            if confirm:
                if t > st_t:
                    if below[t]: seen = True
                    elif seen and above[t]: blocked = False
            elif t - st_t > 20: blocked = False
        if lg:
            pk = max(pk, X[t])
            if X[t] <= 0.85 * ex: lg = False; blocked = True; seen = False; st_t = t
            elif dd[t] > -0.10: lg = False
            elif mode == 0 and low5[t] >= 5: lg = False
            elif mode == 1 and X[t] <= 0.75 * pk: lg = False
            if not lg: continue
            W[t, 0] = min(w, idle[t])
        elif (not blocked) and dd[t] <= -D and (above[t] if confirm else True) and idle[t] >= 0.5:
            lg = True; ex = X[t]; pk = X[t]; W[t, 0] = min(w, idle[t])
    o.update(G=g[:, None], Wt=W, mode=mode, inc=0, RB=np.zeros((T, 1))); return o


# ------------------------------------------------------------------------------------------------ 5. MIDTERM-ADD
NAMES_MID = ('cal:month', 'cal:dom', 'cal:dow', 'cal:ymod4')
_MD = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def _exec_day(v, steps=2):
    """(month, dom, dow, ymod4, valid) of the day `steps` weekdays after each row, from the row's own calendar fields"""
    m0, d0, w0, y0 = (np.asarray(v.x[k], dtype=np.float64) for k in NAMES_MID)
    valid = ~(np.isnan(m0) | np.isnan(d0) | np.isnan(w0) | np.isnan(y0))
    m = np.nan_to_num(m0, nan=1).astype(int); d = np.nan_to_num(d0, nan=1).astype(int); w = np.nan_to_num(w0, nan=0).astype(int)
    y = np.nan_to_num(y0, nan=0).astype(int)
    for _ in range(steps):
        add = np.where(w >= 4, 3, 1); d = d + add; w = (w + add) % 7
        ml = _MD[m - 1] + ((m == 2) & (y == 0)); over = d > ml
        d = np.where(over, d - ml, d); y = np.where(over & (m == 12), (y + 1) % 4, y); m = np.where(over, m % 12 + 1, m)
    return m, d, w, y, valid


def _window(v, start, end):
    m, d, w, y, ok = _exec_day(v)
    if start == 'oct': s = (y == 2) & (m >= 10)
    elif start == 'election':
        fm = (d - w - 1) % 7 + 1; s = (y == 2) & (((m == 11) & (d >= fm + 2)) | (m == 12))
    else: raise ValueError(start)
    lastm = {'jun': 6, 'apr': 4}[end]
    e = (y == 3) & (m <= lastm)
    return (s | e) & ok


def midterm_add(v, start='oct', end='jun', vcap=True, phi=1.0, veh='TQQQ'):
    o = xv1.ref(v); T = v.T; r = v.c.r[0]
    g = cm.fund(v, 'TQQQ', r, 3) if veh == 'TQQQ' else cm.fund(v, 'QLD', r, 2)
    win = _window(v, start, end); vol = v.c.vol(20)[0]
    C = np.where(win, 3.0 if not vcap else np.where(_lt(vol, 0.40) | (vol == 0.40), 3.0, np.where(np.isnan(vol), 0.0, 1.0)), 0.0)
    if not vcap: C = np.where(win, 3.0, 0.0)
    x = np.where(np.isnan(g), 0.0, phi * np.maximum(0.0, C - v.ref_held) / 3.0)
    w = _trade(x, 1.0 / 6.0, T)
    o.update(G=g[:, None], Wt=w[:, None], mode=0, inc=0, RB=np.zeros((T, 1))); return o
