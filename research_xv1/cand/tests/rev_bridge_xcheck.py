"""Reviewer cross-check of bridge.py: an independent, brute-force re-implementation of the four written rules (same reading
choices as the NOTES of bridge.py) is compared with the candidate's Wt, cell by cell, (a) on the real <= 2014 view and
(b) on synthetic views built to hit the corner cases (many episodes, B == 3 with L <= 1, late-starting series).
Only counts of differing cells and activity counts are printed. No performance figure is computed."""
import sys, json, types
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
import cbase as cm
import bridge

import collections
ST = collections.Counter()
SECT = (('semis', 'SOXL', None), ('XLF', 'FAS', 'kf:Money'), ('IWM', 'TNA', 'kf:Lo 10'), ('XLK', 'TECL', 'kf:BusEq'),
        ('XLE', 'ERX', 'kf:Enrgy'), ('IYR', 'DRN', None))


def wmax(a, t, n=756):
    w = a[max(0, t - n + 1):t + 1]; w = w[~np.isnan(w)]
    return w.max() if len(w) else np.nan


def plevel(g):
    """price path of a fund: starts at 1 before the first row; a missing return keeps the price"""
    return np.cumprod(1 + np.nan_to_num(g))


def one_x(v, k, proxy):
    if k == 'semis': return v.x['semis']
    a = v.x['ret:' + k]
    return a if proxy is None else np.where(np.isnan(a), v.x[proxy], a)


def model(r1, rf, L): return L * r1 - (L - 1) * rf - (0.0095 + 0.0075 * (L - 1)) / 252


def fundret(v, key, r1, L):
    a = v.x['ret:' + key]; return np.where(np.isnan(a), model(r1, v.c.rf[0], L), a)


def my_fast(v, B, X, d, w=0.20):
    N = np.asarray(v.c.lvl[0], dtype=float); L = v.ref_target; T = v.T
    if X == 'LOSER':
        R1 = [one_x(v, k, p) for k, _, p in SECT]; G = np.column_stack([fundret(v, f, R1[i], 3) for i, (_, f, _) in enumerate(SECT)])
    elif X == 'TQQQ': G = fundret(v, 'TQQQ', v.c.r[0], 3)[:, None]
    else: G = fundret(v, 'SOXL', v.x['semis'], 3)[:, None]
    W = np.zeros(G.shape); last_high = -10 ** 9; ep = 0; sig_ep = -1; pos = None
    for t in range(T):
        H = wmax(N, t)
        if not np.isnan(N[t]) and N[t] >= H: last_high = t; ep += 1
        if pos is not None:
            s, j = pos
            if (t > s and B[t] == 3) or t - s >= 126: ST['f_exit_a' if B[t] == 3 else 'f_exit_b'] += 1; pos = None
            else: W[t, j] = w
            continue
        if np.isnan(N[t]) or np.isnan(H) or np.isnan(L[t]): continue
        if not (N[t] / H - 1 <= -d and t - last_high <= 63 and L[t] <= 1 and ep != sig_ep): continue
        j = 0
        if X == 'LOSER':
            best = None
            for i in range(len(SECT)):
                if t - 62 < 0: continue
                win = R1[i][t - 62:t + 1]
                if np.isnan(win).any(): continue
                tr = np.prod(1 + win) - 1
                if best is None or tr < best[0]: best = (tr, i)
            if best is None: continue
            j = best[1]
        if np.isnan(G[t, j]): continue
        pos = (t, j); sig_ep = ep; W[t, j] = w; ST['f_signals'] += 1; ST['f_signals_B3'] += int(B[t] == 3)
    return W


def my_staged(v, B, X, depths, budget, use_a, tstop):
    S = plevel(v.x['semis']); S = np.where(np.cumsum(~np.isnan(v.x['semis'])) > 0, S, np.nan); L = v.ref_target; T = v.T
    g = fundret(v, 'SOXL', v.x['semis'], 3) if X == 'SOXL' else fundret(v, 'USD', v.x['semis'], 2)
    P = plevel(g); W = np.zeros((T, 1)); waiting = False; is_open = False; spent = False; fired = set(); tr = []; n_open = 0; tr_ep = None
    for t in range(T):
        H = wmax(S, t); dd = S[t] / H - 1 if not (np.isnan(S[t]) or np.isnan(H)) else np.nan
        if not np.isnan(dd) and S[t] >= H: waiting = True; is_open = False; spent = False; fired = set()
        elif waiting and not np.isnan(dd) and dd <= -depths[0]: waiting = False; is_open = True; spent = False; fired = set(); n_open += 1
        sold = False
        if tr:
            f0 = tr[0]; ca = use_a and t > f0 and B[t] == 3; cc = t - f0 >= tstop; cb = False
            if t >= f0 + 2:
                hi = P[f0 + 2:t + 1].max(); armed = False
                for u in range(f0 + 2, t):
                    fl = [P[s + 2] for s in tr if s + 2 <= u]
                    if P[u] >= 2.0 * (sum(fl) / len(fl)): armed = True; break
                cb = armed and P[t] <= 0.65 * hi
            if ca or cb or cc:
                ST['s_exit_a'] += int(ca); ST['s_exit_b'] += int(cb); ST['s_exit_c'] += int(cc); ST['s_exit_before_fill'] += int(t < f0 + 2); tr = []; spent = True; sold = True
        if not sold:
            older = len(tr) > 0 and tr_ep != n_open            # one budget at a time: a sleeve of an earlier episode is still held
            ST['s_blocked_by_older_sleeve'] += int(older and is_open and not spent and not np.isnan(L[t]) and L[t] <= 1 and not np.isnan(dd) and dd <= -depths[0])
            if is_open and not spent and not older and not np.isnan(L[t]) and L[t] <= 1 and not np.isnan(dd) and not np.isnan(g[t]):
                n0 = len(tr); held0 = n0 > 0 and len(fired) == 0
                for k in range(3):
                    if k not in fired and dd <= -depths[k]:
                        fired.add(k); tr.append(t)
                        if len(tr) == 1: tr_ep = n_open
                ST['s_multi_fire_rows'] += int(len(tr) - n0 > 1); ST['s_merge_rows'] += int(held0 and len(tr) > n0); ST['s_fire_rows_B3'] += int(len(tr) > n0 and B[t] == 3)
            W[t, 0] = len(tr) * budget / 3.0
    return W


def my_panic(v, B, X, theta, w=0.20):
    N = np.asarray(v.c.lvl[0], dtype=float); L = v.ref_target; T = v.T
    with np.errstate(all='ignore'): R = v.c.vix[0] / v.x['lvl:_VIX3M@ext']
    R = np.where(np.isfinite(R), R, np.nan)
    g = fundret(v, 'TQQQ', v.c.r[0], 3) if X == 'TQQQ' else fundret(v, 'SOXL', v.x['semis'], 3)
    W = np.zeros((T, 1)); ep = 0; sig_ep = -1; pos = None
    for t in range(T):
        H = wmax(N, t)
        if not np.isnan(N[t]) and N[t] >= H: ep += 1
        if pos is not None:
            if np.isnan(R[t]) or (t > pos and B[t] == 3) or R[t] >= 1.10 or t - pos >= 63:
                ST['p_exit_nan' if np.isnan(R[t]) else 'p_exit'] += 1; pos = None
            else: W[t, 0] = w
            continue
        if t < 40 or np.isnan(L[t]) or np.isnan(g[t]) or ep == sig_ep: continue
        arm = any((not np.isnan(R[u])) and R[u] >= theta for u in range(t - 40, t - 2))
        calm = all((not np.isnan(R[u])) and R[u] <= 1.00 for u in (t, t - 1, t - 2))
        if arm and calm and L[t] <= 1: pos = t; sig_ep = ep; W[t, 0] = w; ST['p_signals'] += 1
    return W


def mine(e, v, B):
    p = e['params']; f = e['func']
    if f == 'fast_crash': return my_fast(v, B, p['X'], p['d'], p['w'])
    if f == 'staged_bridge': return my_staged(v, B, 'SOXL', bridge.D_SET[p['depth_set']], p['budget'], True, 252)
    if f == 'hold_to_top': return my_staged(v, B, p['X'], (0.40, 0.50, 0.60), 0.20, False, 756)
    if f == 'panic_peak': return my_panic(v, B, p['X'], p['theta'])
    raise ValueError(f)


def compare(tag, cfgs, v, B, quiet=False):
    tot = 0
    for e in cfgs:
        o = getattr(bridge, e['func'])(v, **e['params']); W = np.asarray(o['Wt']); M = mine(e, v, B)
        n = int((np.abs(W - M) > 1e-12).any(axis=1).sum()) if W.shape == M.shape else -1; tot += abs(n)
        ok = (o['mode'] == (1 if e['func'] == 'hold_to_top' else 0)) and o['inc'] == 1 and np.array_equal(o['B'], B)
        if not quiet or n != 0 or not ok:
            print(tag, e['name'], 'rows where Wt differs from the independent version:', n, '| rows with weight', int((W != 0).any(axis=1).sum()),
                  '| weight changes', int((np.diff(W, axis=0) != 0).any(axis=1).sum()), '| mode/inc/B ok', bool(ok), flush=True)
    return tot


def synth(seed, T=5000):
    g = np.random.default_rng(seed)
    def walk(sd, crash=0.004):
        r = g.normal(0.0006, sd, T); j = g.random(T) < crash
        for i in np.flatnonzero(j): r[i:i + 25] -= abs(g.normal(0.012, 0.006))
        return np.clip(r, -0.3, 0.3)
    r = walk(0.018); sem = walk(0.022, 0.006); rf = np.full(T, 0.00012)
    B = np.zeros(T); L = np.zeros(T); t = 0
    while t < T:
        n = int(g.integers(5, 160)); b = g.choice([0.0, 1.0, 3.0], p=[0.35, 0.25, 0.40]); k = g.choice([1.0, 1.0, 0.8, 0.5, 0.3])
        B[t:t + n] = b; L[t:t + n] = b * k; t += n
    if seed % 3 == 0: L[g.random(T) < 0.01] = np.nan
    a = np.cumsum(g.normal(0, 0.06, T)); a -= np.linspace(0, a[-1], T); vix = 20 * np.exp(0.6 * np.sin(np.arange(T) / 37.0) + 0.15 * g.normal(0, 1, T).cumsum() / np.sqrt(np.arange(1, T + 1)) + 0.25 * g.normal(0, 1, T))
    v3 = 20 * np.exp(0.45 * np.sin(np.arange(T) / 37.0 - 0.3) + 0.05 * g.normal(0, 1, T)); v3[:int(g.integers(50, 900))] = np.nan
    if seed % 2 == 0: v3[g.random(T) < 0.01] = np.nan
    x = {'semis': sem.copy(), 'lvl:_VIX3M@ext': v3}
    def late(base, lv, noise=0.004):
        a = lv * base + g.normal(0, noise, T); a[:int(g.integers(200, 3500))] = np.nan; return a
    x['ret:TQQQ'] = late(r, 3); x['ret:SOXL'] = late(sem, 3); x['ret:USD'] = late(sem, 2)
    for k, f, p in SECT[1:]:
        base = walk(0.02, 0.005)
        if p is not None: x[p] = base + g.normal(0, 0.003, T)
        x['ret:' + k] = late(base, 1, 0.001); x['ret:' + f] = late(base, 3)
    c = types.SimpleNamespace(r=[r], rf=[rf], lvl=[np.cumprod(1 + r)], vix=[vix])
    return types.SimpleNamespace(T=T, c=c, x=x, ref_target=L), B


if __name__ == '__main__':
    cfgs = json.load(open('/home/user/-/research_xv1/cand/bridge.configs.json'))
    X = xv1.frame(xv1.OLD_END); names = sorted(set(n for e in cfgs for n in e['names']))
    v = xv1.View(X, xv1.extras(names, X.index)); B = xv1.ref(v)['B']
    print('REAL <= 2014 view: total differing rows', compare('real', cfgs, v, B))
    print('REAL corner counters (all 18 configurations together): tranche rows that add to a sleeve of an earlier episode', ST['s_merge_rows'],
          '| candidate 1 signals on a row with B == 3', ST['f_signals_B3'], '| tranche rows with B == 3', ST['s_fire_rows_B3'], '| candidate 3 exits on NaN R', ST['p_exit_nan']); ST.clear()
    real_ref = xv1.ref; tot = 0; act = 0
    for seed in range(int(sys.argv[1]) if len(sys.argv) > 1 else 40):
        sv, sB = synth(seed)
        xv1.ref = lambda vv, _b=sB: dict(B=_b.copy(), bfn=None, bp=np.zeros(1), fstep=0.5)
        try:
            tot += compare('synthetic seed %d' % seed, cfgs, sv, sB, quiet=True)
            for e in cfgs: act += int((np.asarray(getattr(bridge, e['func'])(sv, **e['params'])['Wt']) != 0).any(axis=1).sum())
        finally: xv1.ref = real_ref
    print('SYNTHETIC views: total differing rows', tot, '| rows with weight over all runs', act)
    print('corner cases hit in the synthetic runs (independent version, counts):', dict(sorted(ST.items())))
