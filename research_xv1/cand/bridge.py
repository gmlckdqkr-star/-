"""Bridge: extreme-market overlays (owner direction: v1 normally, a 3x sleeve only in extreme markets). Four candidates.
All use v1 unchanged (o = xv1.ref(v); B, bfn, bp, fstep untouched) plus extra instruments in G / Wt.

NOTES (reading choices)
 1. Engine terms: every candidate uses inc=1 (tranche semantics: a higher Wt adds (new - old) x account as fresh money, Wt = 0
    sells everything, fixed shares in between), which is the engine's form of "buy for w x equity, filled t+2, then fixed
    shares". The engine sizes a tranche on the account equity at the fill (close t+2), not at the signal close t; candidate
    code cannot change that. The rows carry Wt only; the 2-row delay is the engine's, nothing is shifted here.
    Candidates 1-3: mode 0. Candidate 4: mode 1 on all rows (the same as v1 while no sleeve is held).
 2. X = TQQQ (candidates 1 and 3) is an extra instrument, cm.fund(v, 'TQQQ', Nasdaq-100 return, 3) (the real fund where it
    exists, the model before): the rules say "v1 unchanged", so B is not touched and the sleeve is not expressed through B.
 3. "v1 target level L <= 1": v.ref_target[t] <= 1 (NaN: no signal). "v1 base level = 3 at a close": xv1.ref(v)['B'][t] == 3,
    tested on the rows after the (first) signal row, not on the signal row itself. A signal on a row with B == 3 and L <= 1
    (brake) therefore buys and is sold again by the next row with B == 3 (no such row on the <= 2014 calendar).
 4. 756-day high H: cm.roll_max over the last 756 rows including t. The view has only 300 rows before the first account row, so
    on the first 455 account rows (until 756 view rows exist) the window is the available history. The text of candidate 1 says
    so ("use available history before"); the same is done for the chip series of candidates 2 and 4 and for the episode counter
    of candidate 3, where the text is silent. So T0 = None for candidates 1, 2 and 4. "Closes at H" / high day: close >= H of
    that row (a new high or equal to it). Episode counter = number of high days so far (candidates 1 and 3).
 5. Candidate 1: age = rows since the last high day (a row that closed at its own 756-day high). It is not re-dated when an old
    high leaves the window, so that, as the text says, once age > 63 no buy is possible until a new 756-day high. Signal needs
    dd <= -d, age <= 63, L <= 1, no signal yet in this episode and no position open (the text does not name the last one; if
    the other conditions hold while a position of an earlier episode is open, the signal waits for the first row after that
    position is closed; no such row on the <= 2014 calendar). Exit at the first row t > signal with B == 3, or
    t - signal >= 126: Wt is 0 from that row.
 6. Candidate 1, LOSER: at the signal row the sector with the lowest 63-day total return (product of the last 63 daily 1x
    returns, rows t-62..t; all 63 must exist, otherwise the sector is not eligible on that row) among semis (SOXL), XLF (FAS),
    IWM (TNA), XLK (TECL), XLE (ERX), IYR (DRN); ties: first in this order; the fund is then fixed for the position. 1x series =
    the ETF return where it exists, the proxy before: semis = v.x['semis'] (Chips, then SOXX), XLF = kf:Money, IWM = kf:Lo 10
    (the smallest size group in the project), XLK = kf:BusEq, XLE = kf:Enrgy; IYR has no proxy and is eligible from the row
    its own 63 returns exist (2000). The project holds nine of the twelve Ken French industries; Money, BusEq and Enrgy are
    among them. Fund returns cm.fund(v, KEY, 1x, 3) (real fund where it exists, model on the 1x series before). ERX is used
    as listed (its own leverage after 2020-03), no special handling. If no sector is eligible, or the chosen fund has no
    return on the row: no signal on that row.
 7. Candidate 2 (staged): S = level of v.x['semis']; H = 756-row rolling max of S; dd = S/H - 1. Phase machine: a high day (S >= H)
    arms; the first armed row with dd <= -d1 opens the episode; a new high day ends it (unfired tranches lapse, spent flag clears).
    Tranche k fires on the first row of the open episode with dd <= -d_k and L <= 1, if the episode is not spent; several tranches
    may fire on one row. Each tranche adds budget/3 of the account as weight: the engine cannot hold a currency amount fixed from
    the episode-opening equity, so "budget B x equity of the opening day, a third per tranche" is approximated by B/3 x equity at
    each tranche's own fill. Fill price of a tranche = SOXL close on row signal + 2 (the engine's delay); it only counts from
    the row it is known. Cost-weighted average fill price = sum(cost_k * price_k) / sum(cost_k) over the fills made by row t
    (equal costs: the plain mean of the fill prices). Trailing exit (b): armed on a close >= 2.0 x the average known on that
    close (closes are not re-tested when a later tranche lowers the average); once armed, sell all on a later close <= 0.65 x
    the highest close since the first fill (the same close cannot arm and sell). Time stop (c): t - first tranche signal >= 252.
    Exit (a): B == 3 on a row after the first tranche signal. Any sell-all sets the current episode spent. A sleeve that
    outlives its episode (no exit before the next high day) keeps its exit clock, average and highest close; while it is held
    no tranche of a later episode is bought, and its sale marks the episode then open as spent, so at most one budget is at
    risk at any time, as the text states ("between two 3-year highs at most one budget is at risk"). The case does not occur
    on the <= 2014 calendar.
 8. Candidate 4: the same entry machine with depths (-40,-50,-60)%, budget 20%; no exit (a); exits (b) trailing and 756-row time
    stop; mode 1. "Entry requires idle cash" is represented by the L <= 1 condition only (mode 1 has no idle-cash test; with
    v1 at or below 1x at least two thirds of the account are idle). Instrument SOXL or USD (cm.fund(v, 'USD', semis, 2)); the
    trailing exit uses the held fund's own level.
 9. Candidate 3: R = VIX / VIX3M (v.c.vix[0], the same-day close, and v.x['lvl:_VIX3M@ext']). Arm day: R >= theta; the arm must
    be in rows t-40..t-3 (in any episode). Calm: R <= 1.00 on t, t-1, t-2. Needs L <= 1, no position open, no signal yet in the
    current 756-day-high episode of the Nasdaq-100. Buy 20%. Exit at the first row t > signal with B == 3, or R >= 1.10, or
    t - signal >= 63. NaN R: never an arm day, never calm (no signal); on a row with NaN R an open position is sold (a needed
    input is missing: weight 0). T0 = first calendar row on which VIX and VIX3M both exist ("active from the first date both
    exist"); the first signal is possible three rows later.
10. Rows where the fund return is NaN at a signal: no signal. The weight is 0 on every row before an input exists.
"""
import numpy as np
import xv1
import cbase as cm

D_SET = {'A': (0.30, 0.40, 0.50), 'B': (0.40, 0.50, 0.60)}
_LOSER = (('semis', 'SOXL'), ('XLF', 'FAS'), ('IWM', 'TNA'), ('XLK', 'TECL'), ('XLE', 'ERX'), ('IYR', 'DRN'))
_PROXY = {'XLF': 'kf:Money', 'IWM': 'kf:Lo 10', 'XLK': 'kf:BusEq', 'XLE': 'kf:Enrgy', 'IYR': None}
NAMES_LOSER = ('semis', 'ret:SOXL', 'ret:FAS', 'ret:TNA', 'ret:TECL', 'ret:ERX', 'ret:DRN', 'ret:XLF', 'ret:IWM', 'ret:XLK',
               'ret:XLE', 'ret:IYR', 'kf:Money', 'kf:Lo 10', 'kf:BusEq', 'kf:Enrgy')


def _highs(lvl, n=756):
    H = cm.roll_max(lvl, n); ok = ~np.isnan(H) & ~np.isnan(lvl)
    return H, ok & (lvl >= H), np.where(ok, lvl / np.where(ok, H, 1.0) - 1.0, np.nan)


def _tot_ret(r1, n=63):
    """total return of the last n daily returns (rows t-n+1 .. t); NaN unless all n returns exist"""
    out = np.full(len(r1), np.nan); bad = np.isnan(r1)
    cp = np.r_[1.0, np.cumprod(1 + np.where(bad, 0.0, r1))]; nb = np.cumsum(np.r_[0, bad.astype(int)])
    if len(r1) >= n:
        x = cp[n:] / cp[:-n] - 1; x[(nb[n:] - nb[:-n]) > 0] = np.nan; out[n - 1:] = x
    return out


def _fund1(v, key):
    """(T,) return of the single instrument of candidates 1-4"""
    if key == 'TQQQ': return cm.fund(v, 'TQQQ', v.c.r[0], 3)
    if key == 'SOXL': return cm.fund(v, 'SOXL', v.x['semis'], 3)
    if key == 'USD': return cm.fund(v, 'USD', v.x['semis'], 2)
    raise ValueError(key)


def _finish(o, G, W, mode):
    o.update(G=G, Wt=W, mode=mode, inc=1); return o


# ------------------------------------------------------------------------------------------------ 1. fast-crash bridge
def fast_crash(v, X='TQQQ', d=0.20, w=0.20, age_max=63, tstop=126):
    o = xv1.ref(v); B = o['B']; L = v.ref_target; T = v.T
    N = cm.ndx_level(v); H, high, dd = _highs(N); age = cm.since(high); ep = np.cumsum(high)
    if X == 'LOSER':
        r1 = {}
        for k, _ in _LOSER:
            if k == 'semis': r1[k] = v.x['semis']
            elif _PROXY[k] is None: r1[k] = v.x['ret:' + k]
            else: r1[k] = cm.spliced(v.x['ret:' + k], v.x[_PROXY[k]])
        ret63 = {k: _tot_ret(r1[k], 63) for k, _ in _LOSER}          # NaN unless all 63 returns of the window exist
        G = np.column_stack([cm.fund(v, f, r1[k], 3) for k, f in _LOSER])
    else:
        G = _fund1(v, X)[:, None]
    J = G.shape[1]; W = np.zeros((T, J)); pos = False; sig = -1; col = 0; used = -1
    for t in range(T):
        if pos:
            if (t > sig and B[t] == 3) or t - sig >= tstop: pos = False
            else: W[t, col] = w
            continue
        if np.isnan(dd[t]) or np.isnan(L[t]) or ep[t] == used: continue
        if not (dd[t] <= -d and age[t] <= age_max and L[t] <= 1): continue
        if X == 'LOSER':
            c = [j for j, (k, _) in enumerate(_LOSER) if not np.isnan(ret63[k][t])]
            if not c: continue
            j = min(c, key=lambda j: ret63[_LOSER[j][0]][t])
        else: j = 0
        if np.isnan(G[t, j]): continue
        pos = True; sig = t; col = j; used = ep[t]; W[t, j] = w
    return _finish(o, G, W, 0)


# ------------------------------------------------------------------------------------------------ 2. and 4. staged
def _staged(v, X, depths, budget, exit_b3, tstop):
    o = xv1.ref(v); B = o['B']; L = v.ref_target; T = v.T
    S = cm.level(v.x['semis']); H, high, dd = _highs(S)
    g = _fund1(v, X); lvl = cm.level(g); W = np.zeros((T, 1)); cost = budget / 3.0
    phase = 0; spent = False; done = [False] * 3
    wcur = 0.0; first = -1; fills = []; hi = np.nan; armed = False; ep = 0; pos_ep = -1
    for t in range(T):
        if high[t]: phase = 1; spent = False; done = [False] * 3
        elif phase == 1 and not np.isnan(dd[t]) and dd[t] <= -depths[0]: phase = 2; spent = False; done = [False] * 3; ep += 1
        if wcur > 0:
            ex = (exit_b3 and t > first and B[t] == 3) or (t - first >= tstop)
            if t >= first + 2 and not np.isnan(lvl[t]):
                hi = lvl[t] if np.isnan(hi) else max(hi, lvl[t])
                if armed and lvl[t] <= 0.65 * hi: ex = True
                kn = [(c, lvl[f]) for f, c in fills if f <= t]
                avg = sum(c * p for c, p in kn) / sum(c for c, _ in kn)
                if lvl[t] >= 2.0 * avg: armed = True
            if ex:
                wcur = 0.0; first = -1; fills = []; hi = np.nan; armed = False; spent = True; W[t, 0] = 0.0
                continue
            W[t, 0] = wcur
        if phase == 2 and not spent and (wcur == 0.0 or pos_ep == ep) and not np.isnan(L[t]) and L[t] <= 1 and not np.isnan(dd[t]) and not np.isnan(g[t]):
            for k in range(3):
                if not done[k] and dd[t] <= -depths[k]:
                    done[k] = True; wcur += cost
                    if first < 0: first = t; hi = np.nan; armed = False; pos_ep = ep
                    fills.append((t + 2, cost))
            W[t, 0] = wcur
    return o, g[:, None], W


def staged_bridge(v, X='SOXL', depth_set='A', budget=0.10):
    o, G, W = _staged(v, X, D_SET[depth_set], budget, True, 252)
    return _finish(o, G, W, 0)


def hold_to_top(v, X='SOXL', depth_set='B', budget=0.20):
    o, G, W = _staged(v, X, D_SET[depth_set], budget, False, 756)
    return _finish(o, G, W, 1)


# ------------------------------------------------------------------------------------------------ 3. panic-peak bridge
def panic_peak(v, X='TQQQ', theta=1.25, w=0.20, arm_lo=40, arm_hi=3, reinv=1.10, tstop=63):
    o = xv1.ref(v); B = o['B']; L = v.ref_target; T = v.T
    vix = v.c.vix[0]; v3 = v.x['lvl:_VIX3M@ext']
    with np.errstate(all='ignore'): R = vix / v3
    R = np.where(np.isfinite(R), R, np.nan)
    with np.errstate(invalid='ignore'): arm = R >= theta; calm = R <= 1.0
    cs = np.r_[0, np.cumsum(arm)]; k = cm.consec(calm)
    N = cm.ndx_level(v); _, high, _ = _highs(N); ep = np.cumsum(high)
    g = _fund1(v, X); W = np.zeros((T, 1)); pos = False; sig = -1; used = -1
    for t in range(T):
        if pos:
            if np.isnan(R[t]) or (t > sig and B[t] == 3) or R[t] >= reinv or t - sig >= tstop: pos = False
            else: W[t, 0] = w
            continue
        if np.isnan(R[t]) or np.isnan(L[t]) or np.isnan(g[t]) or ep[t] == used or t - arm_lo < 0: continue
        if cs[t - arm_hi + 1] - cs[t - arm_lo] > 0 and k[t] >= 3 and L[t] <= 1:
            pos = True; sig = t; used = ep[t]; W[t, 0] = w
    return _finish(o, g[:, None], W, 0)
