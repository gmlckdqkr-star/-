"""Reviewer diagnostics for cand/states.py: mechanics only (v1 level states around sleeve entries, flags). No performance figure."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, pandas as pd, xv1, cbase as cm
cfgs = {e['name']: e for e in json.load(open('/home/user/-/research_xv1/cand/states.configs.json'))}
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(['ret:SOXL', 'semis', 'ret:QLD'], X.index)); T = v.T; i0 = len(X) - T
D_ = lambda t: str(X.index[i0 + int(t)].date())
held = v.ref_held; tgt = v.ref_target; B0 = xv1.ref(v)['B']
print('v1 held values', sorted(set(np.round(held, 6).tolist())))
for n in ('PRXS_P1', 'PRXS_P3', 'PRXS_P4', 'PRXQ_P1'):
    o = xv1.Config(**cfgs[n]).make(v); W = np.asarray(o['Wt'])[:, 0]; on = W != 0
    st = np.flatnonzero(on & ~np.r_[False, on[:-1]]); en = np.flatnonzero(on & ~np.r_[on[1:], False])
    print(n)
    for a, b in zip(st, en):
        print('  entry', D_(a), 'last weight row', D_(b), 'rows', b - a + 1, '| v1 held te..te+5', np.round(held[a:a + 6], 2).tolist(), '| v1 target te-1..te+3', np.round(tgt[a - 1:a + 4], 2).tolist(),
              '| base B te..te+3', B0[a:a + 4].tolist(), '| held at last..+3', np.round(held[b:b + 4], 2).tolist())
# E3 flag: was the 'above 1.02 x SMA200' flag already true on the entry row?
Xs = cm.semis_level(v); s200 = cm.sma(Xs, 200)
o = xv1.Config(**cfgs['PRXS_P4']).make(v); W = np.asarray(o['Wt'])[:, 0]; on = W != 0
for a in np.flatnonzero(on & ~np.r_[False, on[:-1]]):
    ab = Xs > 1.02 * s200; nxt = a + int(np.argmax(ab[a:]))
    print('  PRXS entry', D_(a), 'above-flag on entry row', bool(ab[a]), 'first row >= entry with X > 1.02 SMA200', D_(nxt), '(+%d rows)' % (nxt - a))
# IVV P1 vs P3
b1 = xv1.Config(**cfgs['IVV_P1']).make(v)['B']; b3 = xv1.Config(**cfgs['IVV_P3']).make(v)['B']; b2 = xv1.Config(**cfgs['IVV_P2']).make(v)['B']
print('IVV P1 vs P3 differing rows', int((b1 != b3).sum()), '| P1 vs P2', int((b1 != b2).sum()))
d = b1 != B0; st = np.flatnonzero(d & ~np.r_[False, d[:-1]]); en = np.flatnonzero(d & ~np.r_[d[1:], False])
print('IVV_P1 lift episodes', [(D_(a), D_(b), int(b - a + 1)) for a, b in zip(st, en)])
S = np.asarray(v.c.F['shock6m'][0], bool); cap = S & (B0 == 1); st = np.flatnonzero(cap & ~np.r_[False, cap[:-1]]); en = np.flatnonzero(cap & ~np.r_[cap[1:], False])
print('v1 shock6m cap episodes (S and B == 1)', [(D_(a), D_(b), int(b - a + 1)) for a, b in zip(st, en)])
print('semis NaN rows', int(np.isnan(v.x['semis']).sum()), '| SOXL NaN after first', int(np.isnan(v.x['ret:SOXL'][np.argmax(~np.isnan(v.x['ret:SOXL'])):]).sum()),
      '| QLD NaN after first', int(np.isnan(v.x['ret:QLD'][np.argmax(~np.isnan(v.x['ret:QLD'])):]).sum()))
