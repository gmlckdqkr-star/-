"""Reviewer diagnostics for cross.py: structure and activity only (counts, dates, flags). No return, level or equity is printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, cbase as cm, cross
names = ['semis', 'ret:SOXL', 'ret:TLT', 'ret:TMF', 'ret:QLD', 'ret:TQQQ', 'cal:month', 'cal:dom', 'cal:dow', 'cal:ymod4']
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(names, X.index)); i0 = len(X) - v.T; T = v.T
D = [str(d.date()) for d in X.index[i0:]]
W0 = 300
print('T', T, 'first row', D[0], 'account start', D[W0], 'last', D[-1])
r = v.c.r[0]; print('rows with NDX return exactly 0: warm-up', int((r[:W0] == 0).sum()), 'account', int((r[W0:] == 0).sum()), 'first non-zero return row', D[int(np.argmax(r != 0))])
for k in names: a = v.x[k]; print(k, 'NaN rows', int(np.isnan(a).sum()), 'first valid', D[int(np.argmax(~np.isnan(a)))], 'NaN after first valid', int(np.isnan(a[int(np.argmax(~np.isnan(a))):]).sum()))
y = v.m['y10']; print('y10 NaN', int(np.isnan(y).sum()), 'rows with zero change', int((np.diff(y) == 0).sum()))

# ---------------------------------------------------------------- v1 level: target vs held
o = xv1.ref(v); tg = v.ref_target; hd = v.ref_held
print('\nv1 level: fstep', o['fstep'])
true3 = np.zeros(T, dtype=bool); true3[:T - 2] = hd[2:] >= 3 - 1e-9      # level in force two rows later = order level decided at close t
acc = np.arange(T) >= W0; acc2 = acc & (np.arange(T) < T - 2)
rd = {'tg>=3': tg >= 3 - 1e-9, 'round0.1>=3': np.round(tg / 0.1) * 0.1 >= 3 - 1e-9, 'round0.5>=3': np.round(tg / 0.5) * 0.5 >= 3 - 1e-9}
# engine order rule replica on the target path
held = 0.0; eng = np.zeros(T)
for t in range(T):
    x = tg[t]; stp = 0.5 if (x >= 1.0 or held >= 1.0) else o['fstep']
    if abs(x - held) >= stp or (x == 0 and held > 0): held = np.round(x / stp) * stp
    eng[t] = held
rd['order-rule replica'] = eng >= 3 - 1e-9
print('account rows', int(acc2.sum()), 'rows where the level in force two rows later is 3:', int((true3 & acc2).sum()))
for k, a in rd.items():
    print('  %-20s rows true %5d | true but level in force at t+2 below 3: %4d | false but level in force at t+2 is 3: %4d' % (k, int((a & acc2).sum()), int((a & ~true3 & acc2).sum()), int((~a & true3 & acc2).sum())))
print('  order-rule replica vs ref_held two rows later: rows that differ', int((np.abs(eng[:T - 2] - hd[2:]) > 1e-9)[W0:].sum()))
u, c = np.unique(np.round(hd[W0:], 3), return_counts=True); print('  held levels (value: rows)', dict(zip(u.tolist(), c.tolist())))
print('  target rows strictly between 2.5 and 3:', int(((tg > 2.5) & (tg < 3 - 1e-9) & acc).sum()), ' between 1 and 2.5:', int(((tg > 1 + 1e-9) & (tg <= 2.5) & acc).sum()))


def episodes(w):
    on = w != 0; st = np.flatnonzero(on & ~np.r_[False, on[:-1]]); en = np.flatnonzero(on & ~np.r_[on[1:], False]); return list(zip(st, en))


cfgs = json.load(open('/home/user/-/research_xv1/cand/cross.configs.json'))
print('\nper configuration: weight values and episodes (first row .. last row with a non-zero weight)')
for e in cfgs:
    c = xv1.Config(**e); vv = xv1.View(X, xv1.extras(c.names, X.index)); m = c.make(vv)
    B = m['B']; nb = np.flatnonzero(B != o['B'])
    line = '%-10s B rows differ %4d' % (e['name'], len(nb))
    if len(nb): line += ' first %s last %s values %s' % (D[nb[0]], D[nb[-1]], sorted(set(np.round(B[nb], 3).tolist())))
    if 'Wt' in m:
        w = np.asarray(m['Wt'])[:, 0]; ep = episodes(w); u, cnt = np.unique(np.round(w[w != 0], 4), return_counts=True)
        line += ' | w rows %d (warm-up %d) values %s mode %d inc %d episodes %d' % (int((w != 0).sum()), int((w[:W0] != 0).sum()), dict(zip(u.tolist(), cnt.tolist())), m['mode'], m['inc'], len(ep))
        line += ' | G NaN rows %d, max w %.3f min w %.3f' % (int(np.isnan(m['G']).sum()), w.max(), w.min())
        print(line)
        print('    ', ' '.join('%s..%s(%d)' % (D[a], D[b], b - a + 1) for a, b in ep[:60]))
    else: print(line)
    assert B.min() >= 0 and B.max() <= 3
