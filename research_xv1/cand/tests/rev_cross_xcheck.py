"""Reviewer cross-check of cross.py: every rule is written a second time, slowly and literally from the rule text (pandas
windows, explicit loops, real dates for the calendar rule), and the outputs (B, Wt) are compared row by row with the candidate
code. Prints mismatch counts only. No return, level or equity is printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, pandas as pd, xv1
names = ['semis', 'ret:SOXL', 'ret:TLT', 'ret:TMF', 'ret:QLD', 'ret:TQQQ', 'cal:month', 'cal:dom', 'cal:dow', 'cal:ymod4']
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(names, X.index)); i0 = len(X) - v.T; T = v.T; W0 = 300
dates = X.index[i0:]; D = [str(d.date()) for d in dates]
r = np.asarray(v.c.r[0], dtype=float); rf = np.asarray(v.c.rf[0], dtype=float); y10 = np.asarray(v.m['y10'], dtype=float)
ref = xv1.ref(v); B0 = ref['B']; held_now = np.asarray(v.ref_held, dtype=float); tgt = np.asarray(v.ref_target, dtype=float)
sh6 = np.asarray(v.c.F['shock6m'][0], dtype=bool); inv = np.asarray(v.c.F['inv'][0], dtype=bool)
ndx = pd.Series(np.cumprod(1 + r)); first_real = int(np.argmax(r != 0)); real = np.arange(T) >= first_real
semis = np.asarray(v.x['semis'], dtype=float); S = pd.Series(np.cumprod(1 + semis))
assert not np.isnan(semis).any()


def model(r1, L):
    if L == 3: return 3 * r1 - 2 * rf - 0.0245 / 252
    if L == 2: return 2 * r1 - rf - 0.0170 / 252      # cbase.lev: fee 0.95% + 0.75% per unit borrowed
    raise ValueError


def spl(key, mod): a = np.asarray(v.x[key], dtype=float); return np.where(np.isnan(a), mod, a)


def cmp(name, what, a, b, upto=None):
    a = np.asarray(a, dtype=float).reshape(-1)[:upto]; b = np.asarray(b, dtype=float).reshape(-1)[:upto]
    bad = np.flatnonzero(~(np.isclose(a, b, rtol=0, atol=1e-12) | (np.isnan(a) & np.isnan(b))))
    print('%-10s %-3s rows compared %d mismatches %d %s' % (name, what, len(a), len(bad), ('first ' + D[bad[0]]) if len(bad) else ''), flush=True)
    return len(bad)


# ------------------------------------------------------------------------------------------------ v1 base level, rebuilt
lr = pd.Series(np.log1p(r)); vol20 = (lr.rolling(20).std(ddof=0) * np.sqrt(252)).values
sma200 = ndx.rolling(200).mean().values; nd = ndx.values
cond = inv | sh6; off = np.zeros(T, dtype=bool); st = False
for t in range(T):
    lo = nd[t] < sma200[t] * 0.98; hi = nd[t] > sma200[t] * 1.02
    if st: st = not (hi or not cond[t])
    else: st = bool(lo and cond[t])
    off[t] = st
base = np.where(vol20 > 0.40, 1.0, 3.0)
v1B = np.where(off, 0.0, np.where(sh6, np.minimum(base, 1.0), base))
print('v1 base level rebuilt from the text: mismatches vs xv1.ref', int((np.abs(v1B - B0) > 1e-12).sum()))


def x_sbc(N=252, Lr=3.0, chip=False, always=False):
    q = np.where(real, np.log1p(r), np.nan); b = np.r_[np.nan, -(y10[1:] - y10[:-1])]; minp = min(200, N)
    rho = np.full(T, np.nan)
    for t in range(T):
        a = q[max(0, t - N + 1):t + 1]; c = b[max(0, t - N + 1):t + 1]; ok = ~(np.isnan(a) | np.isnan(c))
        if ok.sum() >= minp and np.std(a[ok]) > 0 and np.std(c[ok]) > 0: rho[t] = np.corrcoef(a[ok], c[ok])[0, 1]
    neg = np.zeros(T, dtype=bool); s = False
    for t in range(T):
        if rho[t] < -0.05: s = True
        elif rho[t] > 0.05: s = False
        neg[t] = s
    if always: neg[:] = True
    rel = neg.copy()
    if chip:
        R = (S / ndx).where(pd.Series(real)); rel &= (R > R.rolling(200).mean()).values
    capped = np.where(sh6, np.where(rel, np.minimum(base, Lr), np.minimum(base, 1.0)), base)
    return np.where(off, 0.0, capped)


# ------------------------------------------------------------------------------------------------ CHIP-LEAD
lvl3 = np.zeros(T, dtype=bool); lvl3[:T - 2] = held_now[2:] >= 3 - 1e-9     # the level in force two rows later (compared on rows < T-2 only)


def x_chip(D=0.40, a=1 / 3, H=252, lead=True):
    s = S.values; hi = S.rolling(756, min_periods=1).max().values; hit = s <= (1 - D) * hi
    DD = np.array([hit[max(0, t - 503):t + 1].any() for t in range(T)])
    m = S.rolling(200).mean().values; UP = np.zeros(T, dtype=bool); u = False
    for t in range(T):
        if np.isnan(m[t]): u = False
        elif s[t] > 1.02 * m[t]: u = True
        elif s[t] < 0.98 * m[t]: u = False
        UP[t] = u
    R = (S / ndx).where(pd.Series(real)); mR = R.rolling(200).mean().values; R = R.values
    LEAD = np.ones(T, dtype=bool)
    if lead:
        l = False; below = 0
        for t in range(T):
            below = below + 1 if R[t] < mR[t] else 0
            if R[t] > mR[t]: l = True
            elif below >= 20: l = False
            LEAD[t] = l
    w = np.zeros(T); active = False; entry = None; cool_until = -1; top = None
    for t in range(T):
        if active:
            top = max(top, s[t]); end = None
            if t - entry >= H: end = 'H'
            elif not UP[t]: end = 'UP'
            elif not LEAD[t]: end = 'LEAD'
            elif s[t] <= 0.80 * top: end = 'STOP'
            if end is not None:
                active = False
                if end != 'H': cool_until = t + 63
            else: w[t] = a if lvl3[t] else 0.0
        elif DD[t] and UP[t] and LEAD[t] and lvl3[t] and t > cool_until:
            active = True; entry = t; top = s[t]; w[t] = a
    return w


# ------------------------------------------------------------------------------------------------ gated long-Treasury fill
def x_tmf(veh='TMF', cap=1.0, useH=True, useE=False):
    dy = np.r_[np.nan, y10[1:] - y10[:-1]]; vals = []; kap = np.full(T, np.nan)
    for t in range(T):
        if r[t] != 0 and dy[t] != 0 and not np.isnan(dy[t]): vals.append(np.sign(r[t]) * np.sign(dy[t]))
        if len(vals) >= 252: kap[t] = np.mean(vals[-252:])
    Hs = np.zeros(T, dtype=bool); h = False
    for t in range(T):
        if kap[t] >= 0.10: h = True
        elif kap[t] <= 0: h = False
        Hs[t] = h
    gate = ~sh6
    if useH: gate = gate & Hs
    if useE: gate = gate & (nd < ndx.rolling(50).mean().values)
    idle = 1 - held_now / 3
    target = np.where(gate, np.minimum(cap, np.floor(10 * idle + 1e-9) / 10), 0.0)
    w = np.zeros(T); cur = 0.0
    for t in range(T):
        if abs(target[t] - cur) >= 0.20 - 1e-9 or (target[t] == 0 and cur > 0): cur = target[t]
        w[t] = cur
    tlt = np.asarray(v.x['ret:TLT'], dtype=float); one = np.where(np.isnan(tlt), np.asarray(v.c.rb[0], dtype=float), tlt)
    g = spl('ret:TMF', model(one, 3)) if veh == 'TMF' else np.where(np.isnan(tlt), np.asarray(v.c.rb[0], dtype=float) - 0.002 / 252, tlt)
    return w, g


# ------------------------------------------------------------------------------------------------ SOXL crash-rebound sleeve
def x_sleeve(D=0.35, confirm=True, mode=0, w=0.15):
    s = S.values; dd = s / S.rolling(756, min_periods=1).max().values - 1; m50 = S.rolling(50).mean().values
    idle = 1 - held_now / 3; out = np.zeros(T)
    long_ = False; blocked = False; was_below = False; stop_row = None; entry_px = None; top = None; low = 0
    for t in range(T):
        low = low + 1 if idle[t] < 0.05 else 0
        if blocked:                                           # block set on an earlier row
            if confirm:
                if s[t] < m50[t]: was_below = True
                elif was_below and s[t] > m50[t]: blocked = False
            elif t - stop_row > 20: blocked = False
        if long_:
            top = max(top, s[t])
            if s[t] <= 0.85 * entry_px: long_ = False; blocked = True; was_below = False; stop_row = t
            elif dd[t] > -0.10: long_ = False
            elif mode == 0 and low >= 5: long_ = False
            elif mode == 1 and s[t] <= 0.75 * top: long_ = False
            if long_: out[t] = min(w, idle[t]) if mode == 0 else w      # mode 1: the sleeve keeps w through v1's re-investment
        elif dd[t] <= -D and (s[t] > m50[t] or not confirm) and idle[t] >= 0.5 and not blocked:
            long_ = True; entry_px = s[t]; top = s[t]; out[t] = min(w, idle[t]) if mode == 0 else w
    return out


# ------------------------------------------------------------------------------------------------ MIDTERM-ADD (real dates)
def election_day(year):
    d = pd.Timestamp(year, 11, 1)
    while d.dayofweek != 0: d += pd.Timedelta(days=1)
    return d + pd.Timedelta(days=1)


def in_window(d, start, end):
    last = 6 if end == 'jun' else 4
    if d.year % 4 == 3: return d.month <= last
    if d.year % 4 != 2: return False
    if start == 'oct': return d.month >= 10
    return d > election_day(d.year)


def x_mid(start='oct', end='jun', vcap=True, phi=1.0, veh='TQQQ'):
    C = np.zeros(T)
    for t in range(T - 2):
        if in_window(dates[t + 2], start, end): C[t] = 3.0 if (not vcap or vol20[t] <= 0.40) else 1.0
    x = phi * np.maximum(0.0, C - held_now) / 3; w = np.zeros(T); cur = 0.0
    for t in range(T):
        if abs(x[t] - cur) >= 1 / 6 - 1e-9 or (x[t] == 0 and cur > 0): cur = x[t]
        w[t] = cur
    g = spl('ret:TQQQ', model(r, 3)) if veh == 'TQQQ' else spl('ret:QLD', model(r, 2))
    return w, g


soxl = spl('ret:SOXL', model(semis, 3)); total = 0
for e in json.load(open('/home/user/-/research_xv1/cand/cross.configs.json')):
    c = xv1.Config(**e); m = c.make(v); p = e['params']; f = e['func']; n = e['name']
    assert m['bfn'] is ref['bfn'] and np.array_equal(m['bp'], ref['bp']) and m['fstep'] == ref['fstep']
    if f == 'sbc_cap':
        total += cmp(n, 'B', m['B'], x_sbc(**p)); assert 'Wt' not in m
        continue
    total += cmp(n, 'B', m['B'], B0)
    if f == 'chip_lead':
        total += cmp(n, 'Wt', m['Wt'], x_chip(**p), T - 2) + cmp(n, 'G', m['G'], soxl); assert (m['mode'], m['inc']) == (1, 0)
    elif f == 'tmf_fill':
        w, g = x_tmf(**p); total += cmp(n, 'Wt', m['Wt'], w) + cmp(n, 'G', m['G'], g); assert (m['mode'], m['inc']) == (0, 0)
    elif f == 'soxl_sleeve':
        total += cmp(n, 'Wt', m['Wt'], x_sleeve(**p)) + cmp(n, 'G', m['G'], soxl); assert (m['mode'], m['inc']) == (p['mode'], 0)
    elif f == 'midterm_add':
        w, g = x_mid(**p); total += cmp(n, 'Wt', m['Wt'], w, T - 2) + cmp(n, 'G', m['G'], g); assert (m['mode'], m['inc']) == (0, 0)
    assert not np.asarray(m.get('RB', 0)).any() and m.get('up') is None and m.get('dn') is None
print('TOTAL mismatches', total)
