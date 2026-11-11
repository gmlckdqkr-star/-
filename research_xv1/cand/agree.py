"""Candidates of the 'agree' package (formula-reliability spec, candidates 2, 3, 4; candidate 1 REL-SCREEN is a search, not implemented).

NOTES (reading choices)
 1. X = 1x semiconductor level (cm.semis_level: Ken French Chips until SOXX exists, SOXX after). Q = Nasdaq-100 level cm.ndx_level
    (index; the spec's 'QQQ before 1999' proxy is the index itself). rho = X/Q. SMA100(rho) = simple mean of the last 100 rho.
 2. Breadth = cm.breadth(v): nine sector slots (SPDR once it has 200 rows, else Ken French industry). Only NINE French industries
    exist in the project (spec names 12) and the spec's sector set is the 9 SPDRs; threshold 'at least 2/3' means share >= 6/9.
 3. Trend flag = cm.trend_flag (1.02 / 0.98 around SMA200, off while the average does not exist). Hi252 = cm.roll_max(level, 252)
    including row t. 'X >= 0.92*Hi252' uses >=. 'calm' = vol20 <= 1.25*vol120 with cm.vol (annualised, log returns).
 4. Rows where any input of a rule's conditions is NaN are 'invalid': the candidate then holds what v1 holds (or cash when v1 is
    off), weight 0, runs of consecutive closes restart, and state machines are set OFF.
 5. 'K = 4 on three consecutive closes': the run counts the row t itself (cm.consec >= 3). OFF is tested before ON.
 6. AGREE-4 OFF rule: OFF when a1 = 0 at the close, or K <= 2 on three consecutive closes. B4 (ON at K >= 3): ON when K >= 3 on
    three consecutive closes; OFF rule unchanged.
 7. Vehicle ladder with 0.03 margin: current class c (0 SOXL, 1 USD, 2 SOXX) moves up when sig20 >= boundary + 0.03 (boundaries
    0.30, 0.45) and down when sig20 < boundary - 0.03; first valid row takes the raw class. The class is tracked on every valid
    row (also while OFF), so a position opened later uses the tracked class. PURE-LADDER (candidate 4) does not state a margin:
    its vehicle is chosen on the plain thresholds of the row (SOXL < 0.30 <= USD < 0.45 <= SOXX; TQQQ < 0.25 <= QLD < 0.35 <= QQQ).
 8. Vehicles: SOXL = cm.fund(SOXL, semis, 3); USD = cm.fund(USD, semis, 2); SOXX = ret:SOXX spliced with semis; QLD = cm.fund(QLD,
    ndx r, 2); QQQ = ret:QQQ spliced with cm.lev(r,rf,1); PSQ = cm.fund(PSQ, ndx r, -1). TQQQ in the ladder is expressed as B = 3.
 9. B5 / QQQ-AGREE 'base level 1 solely because of the caution flag': caution_only = (v1 B == 1) & F['shock6m'] & vol20(NDX) <= 0.40.
    In v1 (fam4: B = 3 or 1 when vol20 > 0.40, min(B, 1) when shock6m, 0 when its trend gate is off) B == 1 together with the
    flag and vol <= 0.40 means the trend gate is not off, i.e. 'Nasdaq trend flag up' is v1's own gate. B5 weight = w_max when ON and
    caution_only on that row.
10. QQQ-AGREE ADD: the state turns ON when caution_only holds and K_Q = 6 on three consecutive closes; it turns OFF when K_Q <= 4
    on three consecutive closes or b1 = 0. While ON, B is set to L_add only on rows where caution_only holds (v1 base is 1 for the
    caution flag alone); elsewhere v1's own base is kept. The brake stays as in v1.
11. b3 momentum = Q > Q[t-126] and Q > Q[t-21] (strict).
12. QQQ-AGREE PSQ: 'v1 level 0' = v.ref_target == 0, 'above 0' = ref_target > 0. Entry needs: v1 level 0, b1 off for >= 42 consecutive
    closes, Q < 0.80*Hi252, Q < Q[t-126], rho < SMA100(rho). Exit when ref_target > 0, or b1 on, or Q > Q[t-21] on 5 consecutive
    closes. After an exit a new entry needs all entry conditions again and the 5-close exit run must not be running at that row.
13. PURE-LADDER: raw rung each close (1..5), a rung change needs 3 consecutive closes (cm.debounce on the raw rung; invalid rows count
    as rung 5 = cash and force cash). Bear unanimity = Nasdaq trend flag off >= 42 closes & Q < 0.80*Hi252 & Q < Q[t-126] &
    rho < SMA100(rho); rung 4 = 50% PSQ, 50% cash (no rebalancing, drifts). E2 uses rungs 1 and 5 only, E3 rungs 2..5 only (K_X
    ignored; K_Q >= 5 -> Nasdaq vehicle). v1 off: B = 0 except TQQQ rung (B = 3), no brake, mode 1, inc 0, one instrument at a time.
14. K_X in PURE-LADDER has six terms (X trend, rho, breadth, calm of X, momentum of X, X near high); K_Q likewise on Q with the
    shared rho and breadth. In AGREE-4, a4 (calm) uses X; in QQQ-AGREE b4 uses Q.
"""
import numpy as np
import xv1
import cbase as cm

NAMES_SEMI = ('ret:SOXL', 'ret:USD', 'ret:SOXX', 'semis') + cm.SECTOR_NAMES
NAMES_NDX = ('ret:PSQ',) + cm.SECTOR_NAMES + ('semis',)
NAMES_LADDER = ('ret:SOXL', 'ret:USD', 'ret:SOXX', 'ret:QQQ', 'ret:QLD', 'ret:PSQ', 'semis') + cm.SECTOR_NAMES


def _core(v, who):
    """conditions for underlying who in 'X' / 'Q'; returns dict of arrays (bool conditions, K and validity)"""
    X = cm.semis_level(v); Q = cm.ndx_level(v); rho = X / Q
    U = X if who == 'X' else Q
    sma_rho = cm.sma(rho, 100); br = cm.breadth(v)
    ret = v.x['semis'] if who == 'X' else v.c.r[0]
    v20 = cm.vol(ret, 20); v120 = cm.vol(ret, 120)
    s200 = cm.sma(U, 200); hi = cm.roll_max(U, 252); l126 = cm.lag(U, 126); l21 = cm.lag(U, 21)
    valid = ~(np.isnan(U) | np.isnan(sma_rho) | np.isnan(br) | np.isnan(v20) | np.isnan(v120) | np.isnan(s200) | np.isnan(hi)
              | np.isnan(l126) | np.isnan(l21) | np.isnan(Q) | np.isnan(X))
    with np.errstate(invalid='ignore'):
        c = dict(trend=cm.trend_flag(U), lead=rho > sma_rho, breadth=br >= 2 / 3 - 1e-12, calm=v20 <= 1.25 * v120,
                 mom=(U > l126) & (U > l21), high=U >= 0.92 * hi)
    c = {k: np.asarray(a, dtype=bool) & valid for k, a in c.items()}
    c['trend'] = cm.trend_flag(U) & valid
    return dict(c=c, valid=valid, U=U, X=X, Q=Q, rho=rho, sma_rho=sma_rho, hi=hi, l126=l126, l21=l21, v20=v20, v120=v120)


def _vclass(sig, valid, b=(0.30, 0.45), m=0.03):
    out = np.zeros(len(sig), dtype=np.int64); cur = None
    for t in range(len(sig)):
        if not valid[t] or np.isnan(sig[t]): out[t] = 0 if cur is None else cur; continue
        if cur is None: cur = int(sig[t] >= b[0]) + int(sig[t] >= b[1])
        else:
            while cur < len(b) and sig[t] >= b[cur] + m: cur += 1
            while cur > 0 and sig[t] < b[cur - 1] - m: cur -= 1
        out[t] = cur
    return out


def _semis_returns(v):
    s = v.x['semis']
    return [cm.fund(v, 'SOXL', s, 3), cm.fund(v, 'USD', s, 2), cm.spliced(v.x['ret:SOXX'], s)]


def _caution_only(v, oB):
    return (oB == 1) & np.asarray(v.c.F['shock6m'][0], dtype=bool) & (v.c.vol(20)[0] <= 0.40)


def agree4(v, w=0.30, vehicle='ladder', k_on=4, caution_only=False):
    """AGREE-4 SOXL: semis unanimity overlay in v1's idle cash (mode 0). k_on 4 (K = 4) or 3 (K >= 3 turns ON)."""
    o = xv1.ref(v); S = _core(v, 'X'); c = S['c']; valid = S['valid']
    K = c['trend'].astype(int) + c['lead'] + c['breadth'] + c['calm']
    on_run = cm.consec(valid & ((K == 4) if k_on == 4 else (K >= 3))); off_run = cm.consec(valid & (K <= 2))
    st = False; ON = np.zeros(v.T, dtype=bool)
    for t in range(v.T):
        if not valid[t]: st = False
        elif st and ((not c['trend'][t]) or off_run[t] >= 3): st = False
        elif (not st) and on_run[t] >= 3: st = True
        ON[t] = st
    cls = _vclass(S['v20'], valid) if vehicle == 'ladder' else np.full(v.T, 2)
    if caution_only: ON = ON & _caution_only(v, o['B'])
    G = np.column_stack(_semis_returns(v)); W = np.zeros((v.T, 3))
    W[np.arange(v.T), cls] = np.where(ON, w, 0.0)
    o.update(G=G, Wt=W, mode=0, inc=0)
    return o


def qqq_agree(v, l_add=None, psq_w=None):
    """QQQ-AGREE: ADD (lift v1's caution tier to l_add) and/or PSQ extra (weight psq_w, mode 0)."""
    o = xv1.ref(v); S = _core(v, 'Q'); c = S['c']; valid = S['valid']; T = v.T
    K = sum(c[k].astype(int) for k in ('trend', 'high', 'mom', 'calm', 'breadth', 'lead'))
    if l_add is not None:
        co = _caution_only(v, o['B']); r6 = cm.consec(valid & (K == 6)); l4 = cm.consec(valid & (K <= 4))
        st = False; B = o['B'].copy()
        for t in range(T):
            if not valid[t]: st = False
            elif st and ((not c['trend'][t]) or l4[t] >= 3): st = False
            elif (not st) and co[t] and r6[t] >= 3: st = True
            if st and co[t]: B[t] = l_add
        o['B'] = B
    if psq_w is not None:
        Q = S['Q']; off_run = cm.consec(valid & ~c['trend']); up5 = cm.consec(valid & (Q > S['l21']))
        entry = valid & (off_run >= 42) & (Q < 0.80 * S['hi']) & (Q < S['l126']) & (S['rho'] < S['sma_rho'])
        lvl = v.ref_target; st = False; ON = np.zeros(T, dtype=bool)
        for t in range(T):
            if not valid[t]: st = False
            elif st and (lvl[t] > 0 or c['trend'][t] or up5[t] >= 5): st = False
            elif (not st) and entry[t] and lvl[t] == 0 and up5[t] < 5: st = True
            ON[t] = st
        o.update(G=cm.fund(v, 'PSQ', v.c.r[0], -1)[:, None], Wt=np.where(ON, psq_w, 0.0)[:, None], mode=0, inc=0)
    return o


def ladder(v, part='full'):
    """PURE-LADDER: one instrument at a time, v1 switched off. part 'full' (E1), 'soxx' (E2: rungs 1, 5), 'qqq' (E3: rungs 2-5)."""
    T = v.T; SX = _core(v, 'X'); SQ = _core(v, 'Q'); cx = SX['c']; cq = SQ['c']
    valid = SX['valid'] & SQ['valid']
    KX = sum(cx[k].astype(int) for k in ('trend', 'lead', 'breadth', 'calm', 'mom', 'high'))
    KQ = sum(cq[k].astype(int) for k in ('trend', 'high', 'mom', 'calm', 'breadth', 'lead'))
    Q = SQ['Q']; bear = valid & (cm.consec(valid & ~cq['trend']) >= 42) & (Q < 0.80 * SQ['hi']) & (Q < SQ['l126']) & (SQ['rho'] < SQ['sma_rho'])
    raw = np.full(T, 5)
    for t in range(T):
        if not valid[t]: continue
        if part != 'qqq' and KX[t] == 6: raw[t] = 1
        elif part == 'soxx': raw[t] = 5
        elif KQ[t] >= 5: raw[t] = 2
        elif KQ[t] >= 3: raw[t] = 3
        elif bear[t]: raw[t] = 4
    rung = cm.debounce(raw, 3)
    G = np.column_stack(_semis_returns(v) + [cm.fund(v, 'QLD', v.c.r[0], 2), cm.spliced(v.x['ret:QQQ'], cm.lev(v.c.r[0], v.c.rf[0], 1)),
                                            cm.fund(v, 'PSQ', v.c.r[0], -1)])
    W = np.zeros((T, 6)); B = np.zeros(T)
    for t in range(T):
        if not valid[t]: continue
        r = rung[t]
        if r == 1:
            s = SX['v20'][t]; W[t, 0 if s < 0.30 else (1 if s < 0.45 else 2)] = 1.0
        elif r == 2:
            s = SQ['v20'][t]
            if s < 0.25: B[t] = 3.0
            else: W[t, 3 if s < 0.35 else 4] = 1.0
        elif r == 3: W[t, 4] = 1.0
        elif r == 4: W[t, 5] = 0.5
    return dict(B=B, bfn=xv1.std.ident, bp=np.zeros(1), fstep=0.5, G=G, Wt=W, mode=1, inc=0)
