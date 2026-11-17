"""Reviewer cross-check for cand/states.py: an independent, slow re-implementation of every rule (pandas / plain loops,
no cbase), compared cell by cell with what the candidate functions return
  (1) for the 20 registered configurations on the real <= 2014 view (with activity diagnostics: episodes, dates, exit codes),
  (2) for artificial parameter values on the real view (only to reach code paths that the registered points never reach there:
      demotion, slow / fast split, other cut lengths); these are not parameter points and nothing is chosen from them,
  (3) on the same view with the VIX and the semiconductor return replaced by synthetic series, so that every exit (E1..E5,
      X1..X3) is reached, and
  (4) with the index level multiplied by 2 and by 0.5 (the outputs must not change).
Counts, dates and exit codes only. No return, growth or any other performance figure is computed or printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, pandas as pd, xv1

FILE = '/home/user/-/research_xv1/cand/states.py'
cfgs = json.load(open('/home/user/-/research_xv1/cand/states.configs.json'))
X = xv1.frame(xv1.OLD_END)
ALLN = sorted(set(n for e in cfgs for n in e['names']))
v = xv1.View(X, xv1.extras(ALLN, X.index)); T = v.T; i0 = len(X) - T
D_ = lambda t: str(X.index[i0 + int(t)].date())
held = np.asarray(v.ref_held, float).copy()


def prep():
    """module-level series of the current view (called again after the view's inputs were replaced)"""
    global B0, lvl, vix, S, L, VX, vol20, sma200, sma50, off, ung
    B0 = xv1.ref(v)['B']; lvl = np.asarray(v.c.lvl[0], float); vix = np.asarray(v.c.vix[0], float)
    S = np.asarray(v.c.F['shock6m'][0], bool); INV = np.asarray(v.c.F['inv'][0], bool)
    L = pd.Series(lvl); VX = pd.Series(vix)
    vol20 = np.log1p(pd.Series(v.c.r[0])).rolling(20).std(ddof=0).values * np.sqrt(252)
    sma200 = L.rolling(200).mean().values; sma50 = L.rolling(50).mean().values
    # v1 base signal rebuilt from its definition (fam4: 3, 1 if vol20 > 0.40, 1 if shock6m, 0 if the gate is off)
    off = np.zeros(T, bool); st = False; cond = INV | S
    for t in range(T):
        lo = lvl[t] < sma200[t] * 0.98; hi = lvl[t] > sma200[t] * 1.02
        st = (not (hi or not cond[t])) if st else bool(lo and cond[t]); off[t] = st
    with np.errstate(invalid='ignore'):
        Bv = np.where(vol20 > 0.40, 1.0, 3.0); Bv = np.where(S, np.minimum(Bv, 1.0), Bv); Bv = np.where(off, 0.0, Bv)
        ung = np.where(S | (vol20 > 0.40), 1.0, 3.0)
    return int((Bv != B0).sum())


def fcr(A, D=None, upgrade=False, info=None):
    B = B0.copy(); fast = False; H = np.nan; g = -1; dem = False; U = False
    for t in range(T):
        if not off[t]: continue
        if t == 0 or not off[t - 1]:
            g = t; dem = False; U = False; fast = False
            if t - 251 >= 0:
                w = lvl[t - 251:t + 1]; H = np.max(w); h = max(i for i in range(252) if w[i] == H); a = 251 - h; fast = a <= A
                if info is not None: info.append([D_(t), a, fast, 0, 0, 0])
        if not fast: continue
        if info is not None: info[-1][3] += 1
        if D is not None and lvl[t] < (1 - D) * H: dem = True
        if dem:
            if info is not None: info[-1][4] += 1
            B[t] = 0.0; continue
        lev = 1.0
        if upgrade and t >= g + 10:
            if lvl[t] > sma50[t]: U = True
            elif lvl[t] < 0.97 * sma50[t]: U = False
            if U:
                lev = ung[t]
                if info is not None: info[-1][5] += 1
        B[t] = lev
    return B


def pgc(g, c, K, n=63, info=None):
    B = B0.copy(); G = (L / L.shift(n) - 1).values; end = None; t = 0
    while t < T:
        if not np.isnan(G[t]) and G[t] >= g and (end is None or t - end >= 63):
            if info is not None: info.append(D_(t))
            for s in range(t, min(t + K, T)): B[s] = min(B[s], c)
            end = t + K - 1; t = end + 1; continue
        t += 1
    return B


def ivv(mode, k=1.0, info=None):
    A = VX.rolling(21).mean()
    raw = (A < k * A.shift(126)).values if mode == 'D1' else (A < VX.rolling(252).mean()).values
    Z = np.zeros(T, bool); z = False; nt = nf = 0
    for t in range(T):
        nt = nt + 1 if raw[t] else 0; nf = nf + 1 if not raw[t] else 0
        if not z and nt >= 5: z = True
        elif z and nf >= 5: z = False
        Z[t] = z
    with np.errstate(invalid='ignore'): lift = Z & S & ~off & (vol20 <= 0.40)
    if info is not None: info.update(Z_rows=int(Z.sum()), first_Z=D_(np.argmax(Z)) if Z.any() else None, S_rows_not_off=int((S & ~off).sum()), lift_rows=int(lift.sum()))
    return np.where(lift, 3.0, B0)


def panic(a):
    m = VX.rolling(504).median().values; P = VX.rolling(63).max().values; tau = np.full(T, -1)
    for t in range(62, T):
        if not np.isnan(P[t]): tau[t] = max(s for s in range(t - 62, t + 1) if vix[s] == P[t])
    hi5 = VX.rolling(5).max().values
    with np.errstate(invalid='ignore'): pan = P >= a * m; res = pan & (hi5 <= 0.60 * P)
    return m, P, tau, pan, res


def prx_soxl(Dd, W, carry, info=None):
    m, P, tau, pan, res = panic(1.75); Xs = pd.Series(np.cumprod(1 + np.nan_to_num(v.x['semis'])))
    dd = Xs / Xs.rolling(504, min_periods=1).max() - 1; semi = (dd.rolling(63, min_periods=1).min() <= -Dd).values
    s200 = Xs.rolling(200).mean().values; Xs = Xs.values
    Wt = np.zeros(T); op = False; last = -1
    if info is not None: info.update(panic_rows=int(pan.sum()), res_rows=int(res.sum()), semi_rows=int(semi.sum()), res_and_semi=int((res & semi).sum()), ep=[])
    for t in range(T):
        if op:
            why = None
            if Xs[t] <= 0.75 * Xe: why = 'E1'
            elif vix[t] >= 0.85 * Pe: why = 'E2'
            elif above and Xs[t] < 0.98 * s200[t]: why = 'E3'
            elif t - te >= 756: why = 'E4'
            elif carry == 0 and t - te >= 2 and held[t] >= 3.0: why = 'E5'      # only once the entry is in force (2 rows)
            if Xs[t] > 1.02 * s200[t]: above = True
            if why:
                op = False; last = t
                if info is not None: info['ep'][-1] += [D_(t), why, t - te]
            else: Wt[t] = W
        if not op and res[t] and semi[t] and tau[t] > last:
            op = True; te = t; Xe = Xs[t]; Pe = P[t]; above = bool(Xs[t] > 1.02 * s200[t]); Wt[t] = W
            if info is not None: info['ep'].append([D_(t), 'peak ' + D_(tau[t])])
    return Wt


def prx_qld(a, W, info=None):
    m, P, tau, pan, res = panic(a); Wt = np.zeros(T); op = False; last = -1
    if info is not None: info.update(panic_rows=int(pan.sum()), res_rows=int(res.sum()), res_and_off=int((res & off).sum()), ep=[])
    for t in range(T):
        if op:
            why = 'X1' if B0[t] > 0 else 'X2' if vix[t] >= 0.85 * Pe else 'X3' if t - te >= 126 else None
            if why:
                op = False; last = t
                if info is not None: info['ep'][-1] += [D_(t), why, t - te]
            else: Wt[t] = W
        if not op and res[t] and B0[t] == 0 and tau[t] > last:
            op = True; te = t; Pe = P[t]; Wt[t] = W
            if info is not None: info['ep'].append([D_(t), 'peak ' + D_(tau[t])])
    return Wt


def mine(f, p, info):
    if f == 'fast_crash_floor': return fcr(p['A'], p.get('D'), p.get('upgrade', False), info['ep']), None
    if f == 'post_gain_cut': return pgc(p['g'], p['c'], p['K'], p.get('n', 63), info['ep']), None
    if f == 'iv_veto': return ivv(p['mode'], p.get('k', 1.0), info), None
    if f == 'panic_soxl': return B0, prx_soxl(p['D'], p['W'], p['carry'], info)
    if f == 'panic_qld': return B0, prx_qld(p['a'], p['W'], info)


def compare(f, p, names=()):
    c = xv1.Config('x', 'x', FILE, f, p, names); o = c.make(v); info = dict(ep=[]); Bm, Wm = mine(f, p, info)
    Wc = np.asarray(o['Wt'])[:, 0] if 'Wt' in o else np.zeros(T); Wm = np.zeros(T) if Wm is None else Wm
    return o, Wc, int((Bm != o['B']).sum()), int((Wm != Wc).sum()), info


# ------------------------------------------------------------------------------------------- (1) registered configurations
print('v1 base signal rebuilt from its definition: differing rows', prep(), '| values', sorted(set(B0.tolist())), '| OFF rows in the warm-up', int(off[:300].sum()))
fv = int(np.argmax(~np.isnan(vix)))
print('VIX first row', D_(fv), 'NaN after first', int(np.isnan(vix[fv:]).sum()), '| close #147', D_(fv + 146), '#151', D_(fv + 150), '#252', D_(fv + 251),
      '#504', D_(fv + 503), '| first account row', D_(300), '| v1 held values', sorted(set(np.round(held, 6).tolist())))
total = 0
for e in cfgs:
    o, Wc, dB, dW, info = compare(e['func'], e['params'], e['names']); total += dB + dW
    extra = ''
    if 'G' in o:
        G = np.asarray(o['G'])[:, 0]; key = [n for n in e['names'] if n.startswith('ret:')][0]; a = v.x[key]; have = ~np.isnan(a)
        base = v.x['semis'] if 'SOXL' in key else v.c.r[0]; Lx = 3 if 'SOXL' in key else 2
        model = Lx * base - (Lx - 1) * v.c.rf[0] - (0.0095 + 0.0075 * (Lx - 1)) / 252          # cbase.lev
        extra = ' | G: NaN %d, fund rows %d (first %s) equal %s, model rows max abs diff %.1e | mode %s inc %s up %s dn %s RB>0 %d | W values %s' % (
            int(np.isnan(G).sum()), int(have.sum()), D_(np.argmax(have)), bool((G[have] == a[have]).all()), float(np.max(np.abs(G[~have] - model[~have]))),
            o.get('mode'), o.get('inc'), o.get('up'), o.get('dn'), int((np.asarray(o.get('RB', 0)) > 0).sum()), sorted(set(Wc.tolist())))
    act = (o['B'] != B0) | (Wc != 0)
    print('\n%s  B differs from mine on %d rows, Wt on %d rows | active rows %d, first %s, last %s | B values %s%s' % (
        e['name'], dB, dW, int(act.sum()), D_(np.argmax(act)) if act.any() else None, D_(T - 1 - np.argmax(act[::-1])) if act.any() else None,
        sorted(set(o['B'].tolist())), extra))
    ep = info.pop('ep')
    if info: print('   ', info)
    if e['func'] == 'fast_crash_floor':
        print('    OFF episodes with a 252-row window: %d, FAST %d | [start, a, fast, fast rows, demoted rows, upgraded rows]' % (len(ep), sum(x[2] for x in ep)))
        for x in ep: print('     ', x)
    else:
        print('    episodes %d:' % len(ep), ep)
print('\n(1) REGISTERED CONFIGURATIONS, real view: total differing cells', total)

# ------------------------------------------------------------------------------------------- (2) artificial parameters, real view
total = 0
ART = [('fast_crash_floor', dict(A=70)), ('fast_crash_floor', dict(A=250)), ('fast_crash_floor', dict(A=250, D=0.35)), ('fast_crash_floor', dict(A=250, D=0.10)),
       ('fast_crash_floor', dict(A=250, upgrade=True)), ('fast_crash_floor', dict(A=120, D=0.2, upgrade=True)), ('fast_crash_floor', dict(A=0)),
       ('post_gain_cut', dict(g=0.15, c=2.0, K=10)), ('post_gain_cut', dict(g=0.10, c=0.0, K=70)), ('post_gain_cut', dict(g=0.20, c=1.0, K=5, n=126)),
       ('post_gain_cut', dict(g=0.05, c=1.0, K=1)), ('iv_veto', dict(mode='D1', k=1.2)), ('iv_veto', dict(mode='D1', k=0.7))]
for f, p in ART:
    o, Wc, dB, dW, info = compare(f, p); total += dB + dW; ep = info['ep']
    note = 'episodes %d' % len(ep)
    if f == 'fast_crash_floor': note = 'FAST %d of %d, fast rows %d, demoted rows %d, upgraded rows %d' % (sum(x[2] for x in ep), len(ep), sum(x[3] for x in ep), sum(x[4] for x in ep), sum(x[5] for x in ep))
    print('  art', f, p, '| B diff %d, Wt diff %d | rows differing from v1 %d |' % (dB, dW, int((o['B'] != B0).sum())), note)
print('(2) ARTIFICIAL PARAMETERS, real view: total differing cells', total)

# ------------------------------------------------------------------------------------------- (4) level scale (before the view is altered)
bad = 0
for e in cfgs:
    c = xv1.Config(**e); o = c.make(v)
    for f in (2.0, 0.5):
        vs = xv1.View(X, xv1.extras(e['names'], X.index)); vs._shadow = v._shadow; vs.c.lvl = vs.c.lvl * f; vs.c._c.clear(); os_ = c.make(vs)
        for k in ('B', 'G', 'Wt'):
            if k in o: bad += int(np.sum(~((np.asarray(o[k]) == np.asarray(os_[k])) | (np.isnan(np.asarray(o[k], float)) & np.isnan(np.asarray(os_[k], float))))))
print('(4) LEVEL SCALE x2, x0.5: differing cells over all configurations', bad)

# ------------------------------------------------------------------------------------------- (3) synthetic VIX and semiconductor series
total = 0; tally = {}
for seed in range(6):
    g = np.random.default_rng(100 + seed); calm = seed >= 3
    jump = g.random(T) < (1 / 600 if calm else 1 / 250); x = np.zeros(T)
    for t in range(1, T): x[t] = 0.97 * x[t - 1] + 0.04 * g.normal() + (g.uniform(0.6, 1.4) if jump[t] else 0.0)
    sv = 15 * np.exp(x); sv[:fv] = np.nan
    if seed == 5: sv[fv + 900] = np.nan; sv[fv + 3000:fv + 3003] = np.nan          # missing closes inside the series
    rs = g.normal(0, 0.002 if calm else 0.03, T)
    if calm:
        for j in np.flatnonzero(jump): rs[max(j - 20, 0):j + 5] = -0.025 + g.normal(0, 0.002, len(rs[max(j - 20, 0):j + 5]))
    v.c.vix = sv[None, :].copy(); v.x['semis'] = rs.copy(); prep()
    for e in cfgs:
        if e['func'] in ('fast_crash_floor', 'post_gain_cut'): continue
        o, Wc, dB, dW, info = compare(e['func'], e['params'], e['names']); total += dB + dW
        for q in info.get('ep', []):
            if len(q) >= 4: tally[(e['func'], q[3])] = tally.get((e['func'], q[3]), 0) + 1
        if dB + dW: print('  synthetic seed', seed, e['name'], 'B diff', dB, 'Wt diff', dW)
        if e['func'] == 'iv_veto' and seed in (0, 5): print('  synthetic seed', seed, e['name'], 'lift rows', int((o['B'] != B0).sum()), '| B diff', dB)
print('(3) SYNTHETIC VIX / semis, 6 seeds: total differing cells', total, '| exits reached (config count x episodes):', dict(sorted(tally.items())))
