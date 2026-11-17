"""Reviewer's independent, deliberately naive re-implementation of the agree package, written from the rule text
(specs/formula-reliability.md, candidates 2, 3, 4) and compared row by row with cand/agree.py on the <= 2014 calendar.
Only decisions are compared (base level array, target weight array, instrument return arrays for equality). No performance figure.

Nothing of cand/agree.py or cand/cbase.py is used on the naive side (plain Python loops over rows, lists, math).
Readings fixed here (the same as the package NOTES, so that a difference is a coding error and not a reading):
 - population standard deviation (the project's convention), annualised with sqrt(252)
 - Hi252 = highest close of the last 252 rows including t (the rows that exist, on the first 251 view rows)
 - sector slot = the SPDR once it has 200 returns, the paired Ken French industry before (returns spliced, then one level)
 - 'on three consecutive closes' = rows t-2, t-1, t;  OFF / exit conditions win over ON / entry conditions on the same row
"""
import sys, json, math
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, pandas as pd, xv1
import t_world; t_world.old()

NAN = float('nan')
PAIRS = (('XLK', 'BusEq'), ('XLE', 'Enrgy'), ('XLF', 'Money'), ('XLV', 'Hlth'), ('XLU', 'Utils'), ('XLP', 'NoDur'),
         ('XLI', 'Manuf'), ('XLY', 'Shops'), ('XLB', 'Telcm'))
NAMES = ['ret:SOXL', 'ret:USD', 'ret:SOXX', 'ret:QQQ', 'ret:QLD', 'ret:PSQ', 'semis'] + ['ret:' + a for a, _ in PAIRS] + ['kf:' + b for _, b in PAIRS]
X_ = xv1.frame(xv1.OLD_END); I0 = int(X_.index.searchsorted(pd.Timestamp(xv1.ACC_START))) - xv1.WARM; T = len(X_) - I0      # the view rows
def day(t): return str(X_.index[I0 + int(t)].date())
def isn(x): return x != x


# ------------------------------------------------------------------------------------------------ naive primitives
def n_level(ret):
    out = [NAN] * T; lv = None
    for t in range(T):
        r = float(ret[t])
        if not isn(r): lv = (1.0 + r) if lv is None else lv * (1.0 + r)
        out[t] = NAN if lv is None else lv
    return out


def n_sma(x, n):
    out = [NAN] * T
    for t in range(n - 1, T):
        w = x[t - n + 1:t + 1]
        if not any(isn(a) for a in w): out[t] = sum(w) / n
    return out


def n_hi(x, n):
    out = [NAN] * T
    for t in range(T):
        w = [a for a in x[max(0, t - n + 1):t + 1] if not isn(a)]
        if w: out[t] = max(w)
    return out


def n_sig(ret, n):
    out = [NAN] * T
    for t in range(n - 1, T):
        w = [float(a) for a in ret[t - n + 1:t + 1]]
        if any(isn(a) for a in w): continue
        lr = [math.log(1.0 + a) for a in w]; m = sum(lr) / n
        out[t] = math.sqrt(sum((a - m) ** 2 for a in lr) / n * 252.0)
    return out


def n_trend(u, s200):
    out = [False] * T; f = False
    for t in range(T):
        if isn(s200[t]) or isn(u[t]): f = False
        elif u[t] > 1.02 * s200[t]: f = True
        elif u[t] < 0.98 * s200[t]: f = False
        out[t] = f
    return out


def n_breadth():
    """number of the nine sector series above their own SMA200 (None until all nine averages exist)"""
    above = [[None] * T for _ in PAIRS]
    for j, (a, b) in enumerate(PAIRS):
        e = v.x['ret:' + a]; k = v.x['kf:' + b]; cnt = 0; rr = [NAN] * T
        for t in range(T):
            if not isn(float(e[t])): cnt += 1
            rr[t] = float(e[t]) if (cnt >= 200 and not isn(float(e[t]))) else float(k[t])
        lv = n_level(rr); s = n_sma(lv, 200)
        for t in range(T):
            if not isn(s[t]) and not isn(lv[t]): above[j][t] = lv[t] > s[t]
    out = [None] * T
    for t in range(T):
        col = [above[j][t] for j in range(len(PAIRS))]
        if all(c is not None for c in col): out[t] = sum(col)
    return out


def setup(view):
    """build every naive series of one view (the real <= 2014 view, or a made-up one in rev_agree_fuzz.py)"""
    global v, rX, rQ, rf, LX, LQ, RHO, RHO100, NB, SIG, LV, S200, HI, TR, V1B, V1L, SHK
    v = view; assert v.T == T
    rX = [float(a) for a in v.x['semis']]; rQ = [float(a) for a in v.c.r[0]]; rf = [float(a) for a in v.c.rf[0]]
    LX = n_level(rX); LQ = [float(a) for a in v.c.lvl[0]]
    RHO = [LX[t] / LQ[t] if not (isn(LX[t]) or isn(LQ[t])) else NAN for t in range(T)]
    RHO100 = n_sma(RHO, 100); NB = n_breadth()
    SIG = {('X', 20): n_sig(rX, 20), ('X', 120): n_sig(rX, 120), ('Q', 20): n_sig(rQ, 20), ('Q', 120): n_sig(rQ, 120)}
    LV = {'X': LX, 'Q': LQ}; S200 = {k: n_sma(LV[k], 200) for k in 'XQ'}; HI = {k: n_hi(LV[k], 252) for k in 'XQ'}
    TR = {k: n_trend(LV[k], S200[k]) for k in 'XQ'}
    V1B = [float(a) for a in xv1.ref(v)['B']]; V1L = [float(a) for a in v.ref_target]; SHK = [bool(a) for a in v.c.F['shock6m'][0]]


STRICT252 = 'strict252' in sys.argv     # sensitivity only: Hi252 needs 252 rows (the package uses the rows that exist on view rows 0..250)


def ok_row(t, who):
    """every input the conditions of underlying `who` need exists on row t"""
    if t < (251 if STRICT252 else 126): return False
    need = [LX[t], LQ[t], RHO100[t], SIG[(who, 20)][t], SIG[(who, 120)][t], S200[who][t], HI[who][t], LV[who][t - 126], LV[who][t - 21]]
    return NB[t] is not None and not any(isn(a) for a in need)


def conds(t, who):
    """the six conditions of the rule text on row t (trend, leadership, breadth, calm, momentum, near high)"""
    u = LV[who]
    return dict(trend=TR[who][t], lead=RHO[t] > RHO100[t], breadth=NB[t] * 3 >= 2 * len(PAIRS),
                calm=SIG[(who, 20)][t] <= 1.25 * SIG[(who, 120)][t], mom=(u[t] > u[t - 126]) and (u[t] > u[t - 21]), high=u[t] >= 0.92 * HI[who][t])


def caution_only(t):
    """v1's base signal is 1 solely because of the 10-year-yield caution flag (20-day volatility <= 0.40, trend gate not off)"""
    s = SIG[('Q', 20)][t]
    return V1B[t] == 1.0 and SHK[t] and (not isn(s)) and s <= 0.40


def last3(xs, t, f):
    return t >= 2 and all(xs[s] is not None and f(xs[s]) for s in (t - 2, t - 1, t))


# ------------------------------------------------------------------------------------------------ candidate 2
def naive_agree4(w, ladder=True, k_on=4, only_caution=False):
    K = [None] * T; W = np.zeros((T, 3)); on = False; veh = None
    info = dict(on_rows=0, episodes=0, entry_veh_not_raw=0, veh_changes_on=0, rows_on_run_but_a1_off=0, veh_two_class_jumps=0)
    prev_on = False; prev_veh = None
    for t in range(T):
        if not ok_row(t, 'X'):
            on = False; prev_on = False; continue
        c = conds(t, 'X'); K[t] = int(c['trend']) + int(c['lead']) + int(c['breadth']) + int(c['calm'])
        trig = last3(K, t, (lambda k: k == 4) if k_on == 4 else (lambda k: k >= 3)); info['rows_on_run_but_a1_off'] += int(trig and not c['trend'])
        if (not c['trend']) or last3(K, t, lambda k: k <= 2): on = False
        elif trig: on = True
        s = SIG[('X', 20)][t]; raw = 'SOXL' if s < 0.30 else ('USD' if s < 0.45 else 'SOXX'); veh0 = veh
        if veh is None: veh = raw
        elif veh == 'SOXL':
            if s >= 0.45 + 0.03: veh = 'SOXX'
            elif s >= 0.30 + 0.03: veh = 'USD'
        elif veh == 'USD':
            if s >= 0.45 + 0.03: veh = 'SOXX'
            elif s < 0.30 - 0.03: veh = 'SOXL'
        else:
            if s < 0.30 - 0.03: veh = 'SOXL'
            elif s < 0.45 - 0.03: veh = 'USD'
        info['veh_two_class_jumps'] += int(veh0 is not None and {veh0, veh} == {'SOXL', 'SOXX'})
        use = veh if ladder else 'SOXX'
        if on and ((not only_caution) or (caution_only(t) and V1L[t] == 1.0)): W[t, ('SOXL', 'USD', 'SOXX').index(use)] = w   # B5: v1 at exactly 1x
        if on:
            info['on_rows'] += 1
            if not prev_on:
                info['episodes'] += 1; info['entry_veh_not_raw'] += int(veh != raw)
            elif veh != prev_veh: info['veh_changes_on'] += 1
        prev_on = on; prev_veh = veh
    return np.array(V1B), W, info


# ------------------------------------------------------------------------------------------------ candidate 3
def naive_qqq(l_add=None, psq_w=None):
    K = [None] * T; B = np.array(V1B); W = np.zeros((T, 1)); add = False; psq = False; b1off = 0; up = 0
    info = dict(add_state_rows=0, add_episodes=0, psq_rows=0, psq_episodes=0, psq_rows_warmup=0)
    for t in range(T):
        if not ok_row(t, 'Q'):
            add = False; psq = False; b1off = 0; up = 0; continue
        c = conds(t, 'Q'); K[t] = sum(int(c[k]) for k in c); q = LQ
        b1off = 0 if c['trend'] else b1off + 1
        up = up + 1 if q[t] > q[t - 21] else 0
        if l_add is not None:
            was = add
            if (not c['trend']) or last3(K, t, lambda k: k <= 4): add = False
            elif caution_only(t) and last3(K, t, lambda k: k == 6): add = True
            if add and caution_only(t): B[t] = l_add
            info['add_state_rows'] += int(add); info['add_episodes'] += int(add and not was)
        if psq_w is not None:
            was = psq
            if V1L[t] > 0 or c['trend'] or up >= 5: psq = False
            elif V1L[t] == 0 and b1off >= 42 and q[t] < 0.80 * HI['Q'][t] and q[t] < q[t - 126] and RHO[t] < RHO100[t]: psq = True
            if psq: W[t, 0] = psq_w
            info['psq_rows'] += int(psq); info['psq_episodes'] += int(psq and not was); info['psq_rows_warmup'] += int(psq and t < xv1.WARM)
    return B, (W if psq_w is not None else None), info


# ------------------------------------------------------------------------------------------------ candidate 4
def naive_ladder(part):
    raw = [5] * T; rung = [5] * T; cur = 5; B = np.zeros(T); W = np.zeros((T, 6)); b1off = 0
    info = dict(rung_rows={k: 0 for k in (1, 2, 3, 4, 5)}, rung_changes=0, veh_changes_inside_rung=0)
    prev = None
    for t in range(T):
        ok = ok_row(t, 'X') and ok_row(t, 'Q')
        if ok:
            cx = conds(t, 'X'); cq = conds(t, 'Q'); kx = sum(int(a) for a in cx.values()); kq = sum(int(a) for a in cq.values()); q = LQ
            b1off = 0 if cq['trend'] else b1off + 1
            bear = b1off >= 42 and q[t] < 0.80 * HI['Q'][t] and q[t] < q[t - 126] and RHO[t] < RHO100[t]
            if part != 'qqq' and kx == 6: raw[t] = 1
            elif part == 'soxx': raw[t] = 5
            elif kq >= 5: raw[t] = 2
            elif kq in (3, 4): raw[t] = 3
            elif bear: raw[t] = 4
            else: raw[t] = 5
        else: b1off = 0
        if t >= 2 and raw[t] != cur and raw[t] == raw[t - 1] == raw[t - 2]: cur = raw[t]; info['rung_changes'] += 1
        rung[t] = cur
        if not ok: prev = None; continue
        info['rung_rows'][cur] += 1; held = None
        if cur == 1:
            s = SIG[('X', 20)][t]; held = 0 if s < 0.30 else (1 if s < 0.45 else 2); W[t, held] = 1.0
        elif cur == 2:
            s = SIG[('Q', 20)][t]
            if s < 0.25: B[t] = 3.0; held = 'TQQQ'
            elif s < 0.35: W[t, 3] = 1.0; held = 3
            else: W[t, 4] = 1.0; held = 4
        elif cur == 3: W[t, 4] = 1.0; held = 4
        elif cur == 4: W[t, 5] = 0.5; held = 5
        if prev is not None and prev[0] == cur and prev[1] != held: info['veh_changes_inside_rung'] += 1
        prev = (cur, held)
    return B, W, info


# ------------------------------------------------------------------------------------------------ instruments
def naive_funds():
    def col(key, base, L):
        a = v.x['ret:' + key]; out = np.empty(T)
        for t in range(T):
            if not isn(float(a[t])): out[t] = float(a[t]); continue
            if L == 3: out[t] = 3 * base[t] - 2 * rf[t] - 0.0245 / 252
            elif L == 2: out[t] = 2 * base[t] - rf[t] - (0.0095 + 0.0075) / 252          # the 2x model: fee 0.95% + 0.75% per unit borrowed
            elif L == -1: out[t] = -base[t] + rf[t] - 0.0095 / 252
            elif L == 1: out[t] = base[t] - 0.002 / 252
            elif L == 0: out[t] = base[t] - 0.002 / 252                                 # SOXX vehicle before SOXX exists: Chips less the plain index-fund cost
        return out
    return dict(SOXL=col('SOXL', rX, 3), USD=col('USD', rX, 2), SOXX=col('SOXX', rX, 0), QLD=col('QLD', rQ, 2), QQQ=col('QQQ', rQ, 1), PSQ=col('PSQ', rQ, -1))


def ndiff(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if a.ndim == 1: a = a[:, None]
    if b.ndim == 1: b = b[:, None]
    if a.shape != b.shape: return -1, None
    bad = np.flatnonzero((a != b).any(axis=1))
    return len(bad), bad


def close_cells(a, b, tol=1e-15):
    """instrument return arrays: number of cells that differ by more than tol (the splice is a different arithmetic order)"""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float); na = np.isnan(a); nb = np.isnan(b)
    return int((na != nb).sum() + (np.abs(np.where(na | nb, 0.0, a) - np.where(na | nb, 0.0, b)) > tol).sum())


def compare(view, verbose=True):
    """package against the naive rule on one view, every configuration; returns the total number of differences"""
    setup(view)
    cfgs = json.load(open('/home/user/-/research_xv1/cand/agree.configs.json')); total = 0; F = naive_funds()
    for e in cfgs:
        c = xv1.Config(**e); o = c.make(v); p = e['params']
        if e['func'] == 'agree4':
            B, W, info = naive_agree4(p['w'], ladder=p.get('vehicle', 'ladder') == 'ladder', k_on=p.get('k_on', 4), only_caution=p.get('caution_only', False))
            G = np.column_stack([F['SOXL'], F['USD'], F['SOXX']]); mode = 0
        elif e['func'] == 'qqq_agree':
            B, W, info = naive_qqq(p.get('l_add'), p.get('psq_w')); G = F['PSQ'][:, None] if W is not None else None; mode = 0
        else:
            B, W, info = naive_ladder(p['part']); G = np.column_stack([F[k] for k in ('SOXL', 'USD', 'SOXX', 'QLD', 'QQQ', 'PSQ')]); mode = 1
        nb, badb = ndiff(o['B'], B)
        if W is None: nw, badw = (0, None) if 'Wt' not in o else (int((np.asarray(o['Wt']) != 0).any(axis=1).sum()), None); ng = 0
        else:
            nw, badw = ndiff(o['Wt'], W); ng = close_cells(o['G'], G) if np.asarray(o['G']).shape == G.shape else -1
        okmode = (o.get('mode', 0) == mode) and (o.get('inc', 0) == 0) and all(k not in o for k in ('RB', 'up', 'dn'))
        total += abs(nb) + abs(nw) + abs(ng) + int(not okmode)
        if verbose or nb or nw or ng or not okmode:
            print(e['name'], 'rows_B_differ', nb, 'rows_W_differ', nw, 'G_cells_differ', ng, 'mode/inc/bands as the rule', okmode, '|', info, flush=True)
        for nm, bad in (('B', badb), ('W', badw)):
            if bad is not None and len(bad): print('    first differing rows', nm, [(int(t), day(t)) for t in bad[:8]], 'last', (int(bad[-1]), day(bad[-1])))
    return total


if __name__ == '__main__':
    print('TOTAL differences', compare(xv1.View(X_, xv1.extras(NAMES, X_.index))))
