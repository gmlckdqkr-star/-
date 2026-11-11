"""Reviewer diagnostics for bridge.py: data existence dates, activity counts, first / last active row of every weight
episode as a date. No performance figure is computed or printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
import cbase as cm
cfgs = json.load(open('/home/user/-/research_xv1/cand/bridge.configs.json'))
X = xv1.frame(xv1.OLD_END)
allnames = sorted(set(n for e in cfgs for n in e['names']))
v = xv1.View(X, xv1.extras(allnames, X.index)); i0 = len(X) - v.T; D = X.index
dt = lambda t: str(D[i0 + t].date())
print('T', v.T, 'view row 0', dt(0), 'account row 0 (view row 300)', dt(300), 'view row 755 (first full 756-row window)', dt(755), 'last', dt(v.T - 1))
vix = v.c.vix[0]; v3 = v.x['lvl:_VIX3M@ext']
fv = int(np.flatnonzero(~np.isnan(vix))[0]); f3 = int(np.flatnonzero(~np.isnan(v3))[0]); fb = int(np.flatnonzero(~np.isnan(vix) & ~np.isnan(v3))[0])
print('first VIX row', dt(fv), 'first VIX3M row', dt(f3), 'first row with both', dt(fb), 'rows with R after that', int((~np.isnan(vix / v3))[fb:].sum()), 'NaN R rows after that', int(np.isnan(vix / v3)[fb:].sum()))
for k in allnames:
    a = v.x[k]; ok = ~np.isnan(a)
    if not ok.any(): print(k, 'ALL NaN'); continue
    f = int(np.flatnonzero(ok)[0]); print('%-16s first valid %s  NaN rows after first valid %d' % (k, dt(f), int((~ok[f:]).sum())))
r = xv1.ref(v); B = r['B']; L = v.ref_target
print('B values', sorted(set(np.unique(B).tolist())), 'rows B==3 & L<=1 (account rows)', int(((B == 3) & (L <= 1))[300:].sum()), 'NaN L', int(np.isnan(L).sum()))
for e in cfgs:
    c = xv1.Config(**e); o = c.make(v); W = np.asarray(o['Wt']); G = np.asarray(o['G']); on = (W != 0).any(axis=1)
    st = np.flatnonzero(np.diff(np.r_[0, on.astype(int)]) == 1); en = np.flatnonzero(np.diff(np.r_[on.astype(int), 0]) == -1)
    gbad = 0
    for j in range(G.shape[1]):
        ok = ~np.isnan(G[:, j]); f = int(np.flatnonzero(ok)[0]); gbad += int((~ok[f:]).sum())
    print(e['name'], 'mode', o['mode'], 'inc', o['inc'], 'J', W.shape[1], 'warm-up rows with weight', int(on[:300].sum()), 'rows with weight before view row 755', int(on[:755].sum()),
          'max weight sum %.4f' % W.sum(axis=1).max(), 'G NaN after first valid', gbad, 'B same as v1', bool(np.array_equal(o['B'], B)))
    for a, b in zip(st, en):
        cols = sorted(set(np.flatnonzero((W[a:b + 1] != 0).any(axis=0)).tolist())); lv = sorted(set(np.round(W[a:b + 1].sum(axis=1), 6).tolist()))
        print('    episode', dt(a), '..', dt(b), 'rows', int(b - a + 1), 'columns', cols, 'weight levels', lv)
