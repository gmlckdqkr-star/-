"""Reviewer diagnostics 2 for cross.py: structure only (flags, counts, dates). No return, level or equity is printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, cbase as cm, cross
names = ['semis', 'ret:SOXL', 'ret:TLT', 'ret:TMF', 'ret:QLD', 'ret:TQQQ', 'cal:month', 'cal:dom', 'cal:dow', 'cal:ymod4']
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(names, X.index)); i0 = len(X) - v.T; T = v.T
D = [str(d.date()) for d in X.index[i0:]]; W0 = 300
o = xv1.ref(v); B0 = o['B']; tg = v.ref_target; hd = v.ref_held

# ---------------------------------------------------------------- SBC: effect of the rows on which the index does not exist (return filled with 0)
r = v.c.r[0]; q = np.log1p(r); b = -cross._dy(v); exists = np.cumsum(r != 0) > 0; qm = np.where(exists, q, np.nan)
cau = np.asarray(v.c.F['shock6m'][0], dtype=bool)
print('caution rows (account)', int(cau[W0:].sum()), 'of them with v1 base not 0:', int((cau & (B0 != 0))[W0:].sum()), 'first', D[int(np.argmax(cau & (B0 != 0) & (np.arange(T) >= W0)))])
for N in (126, 252, 504):
    mp = min(200, N)
    r0 = cross._roll_corr(q, b, N, mp); r1 = cross._roll_corr(qm, b, N, mp)
    n0 = cm.hyst(cross._lt(r0, -0.05), cross._gt(r0, 0.05)); n1 = cm.hyst(cross._lt(r1, -0.05), cross._gt(r1, 0.05))
    f0 = int(np.argmax(~np.isnan(r0))); f1 = int(np.argmax(~np.isnan(r1))); dn = np.flatnonzero(n0 != n1)
    print('N', N, 'rho first valid: zero-filled', D[f0], 'masked', D[f1], '| NEG rows on: zero-filled', int(n0.sum()), 'masked', int(n1.sum()), '| rows NEG differs', len(dn),
          ('first %s last %s' % (D[dn[0]], D[dn[-1]])) if len(dn) else '', '| rows NEG differs on caution rows with base not 0:', int(((n0 != n1) & cau & (B0 != 0)).sum()),
          '| NEG switches (masked)', int((np.diff(n1.astype(int)) != 0).sum()))
    sw = np.flatnonzero(np.diff(n1.astype(int)) != 0) + 1
    print('    masked NEG switch dates:', ' '.join('%s%s' % (D[t], '+' if n1[t] else '-') for t in sw[:40]))
# P5 chip confirmation: SMA200 of S/NDX, contaminated rows
R = cm.semis_level(v) / cm.ndx_level(v); s = cm.sma(R, 200); print('P5: S/NDX SMA200 first valid', D[int(np.argmax(~np.isnan(s)))], '; first row with 200 real index levels', D[int(np.argmax(np.cumsum(exists) >= 199))])

# ---------------------------------------------------------------- CHIP-LEAD: 'v1 final level is 3' inside the active windows
held = 0.0; eng = np.zeros(T)
for t in range(T):
    x = tg[t]; stp = 0.5 if (x >= 1.0 or held >= 1.0) else o['fstep']
    if abs(x - held) >= stp or (x == 0 and held > 0): held = np.round(x / stp) * stp
    eng[t] = held
true3 = eng >= 3 - 1e-9; impl3 = np.round(tg / o['fstep']) * o['fstep'] >= 3.0 - 1e-9
dd = np.flatnonzero(true3 != impl3); print('\nL3 rows differ (all rows)', len(dd), 'dates:', ' '.join(D[t] for t in dd[:90]))
cfgs = json.load(open('/home/user/-/research_xv1/cand/cross.configs.json'))
for e in cfgs:
    if e['func'] != 'chip_lead': continue
    c = xv1.Config(**e); m = c.make(v); w = np.asarray(m['Wt'])[:, 0]
    fut3 = np.zeros(T, dtype=bool); fut3[:T - 2] = hd[2:] >= 3 - 1e-9
    print(e['name'], 'rows w>0 while v1 level in force two rows later is below 3:', int(((w > 0) & ~fut3)[:T - 2].sum()))
