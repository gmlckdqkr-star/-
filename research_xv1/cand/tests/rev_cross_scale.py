"""Reviewer checks of cross.py that need no account: (1) level-scale invariance (the index level handed to the candidate is
multiplied by 2 and by 0.5; every output must stay bit-identical), (2) effect of the review fixes on the outputs (rows changed),
(3) CHIP-LEAD window log: entry row, end row, reason (dates and reasons only). No return, level or equity is printed."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, cbase as cm, cross
cfgs = json.load(open('/home/user/-/research_xv1/cand/cross.configs.json'))
X = xv1.frame(xv1.OLD_END); allnames = sorted(set(n for e in cfgs for n in e['names'])); E = xv1.extras(allnames, X.index)
v = xv1.View(X, E); i0 = len(X) - v.T; T = v.T; D = [str(d.date()) for d in X.index[i0:]]


def same(a, b): a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float); return a.shape == b.shape and bool(((a == b) | (np.isnan(a) & np.isnan(b))).all())


print('(1) level-scale invariance')
bad = 0
for e in cfgs:
    c = xv1.Config(**e); m = c.make(v); n = 0
    for f in (2.0, 0.5):
        vs = xv1.View(X, E); vs.c.lvl = vs.c.lvl * f; vs.c._c.clear(); ms = c.make(vs)
        for k in ('B', 'G', 'Wt', 'RB'):
            if k in m: n += not same(m[k], ms[k])
    bad += n
    if n: print('  ', e['name'], 'outputs change with the level scale:', n)
print('   configurations with a scale-dependent output:', bad)

print('(2) rows changed by the review fixes (old reading: target rounded to 0.1 for "level is 3"; index rows before its start used as data)')
new_level = cross._v1_level; new_ok = cross._ndx_ok
for e in cfgs:
    if e['func'] not in ('chip_lead', 'sbc_cap'): continue
    c = xv1.Config(**e); m = c.make(v); M = xv1._MOD[c.file]      # the module object the configuration runs
    keep = (M._v1_level, M._ndx_ok)
    M._v1_level = lambda vv, fstep, step=0.5: np.round(np.asarray(vv.ref_target) / fstep) * fstep
    m1 = c.make(v); M._v1_level = keep[0]
    M._ndx_ok = lambda vv: np.ones(vv.T, dtype=bool)
    m2 = c.make(v); M._ndx_ok = keep[1]
    k = 'Wt' if 'Wt' in m else 'B'
    d1 = np.flatnonzero((np.asarray(m[k]) != np.asarray(m1[k])).reshape(T, -1).any(axis=1)); d2 = np.flatnonzero((np.asarray(m[k]) != np.asarray(m2[k])).reshape(T, -1).any(axis=1))
    print('  %-8s %s rows changed by the level-3 fix: %d %s | by the index-start mask: %d' % (e['name'], k, len(d1), (' '.join(D[t] for t in d1[:12])) if len(d1) else '', len(d2)))

print('(3) CHIP-LEAD windows (entry .. end row, reason)')
o = xv1.ref(v)
for e in cfgs:
    if e['func'] != 'chip_lead': continue
    p = dict(D=0.40, a=1 / 3, H=252, lead=True); p.update(e['params'])
    S = cm.semis_level(v); Q = cm.ndx_level(v); Hmax = cm.roll_max(S, 756); f = S <= (1 - p['D']) * Hmax
    DD = np.array([f[max(0, t - 503):t + 1].any() for t in range(T)]); UP = cm.trend_flag(S, 200, 0.02)
    R = np.where(cross._ndx_ok(v), S / Q, np.nan); sR = cm.sma(R, 200)
    LEAD = cm.hyst(cross._gt(R, sR), cm.consec(cross._lt(R, sR)) >= 20) if p['lead'] else np.ones(T, dtype=bool)
    L3 = cross._v1_level(v, o['fstep']) >= 3 - 1e-9
    w = np.asarray(xv1.Config(**e).make(v)['Wt'])[:, 0]
    log = []; act = False; blocked = -1
    for t in range(T):
        if act:
            pk = max(pk, S[t]); why = 'H' if t - ent >= p['H'] else ('UP' if not UP[t] else ('LEAD' if not LEAD[t] else ('STOP' if S[t] <= 0.8 * pk else None)))
            if why:
                act = False; log.append('%s..%s(%d,%s,w-rows %d)' % (D[ent], D[t], t - ent, why, int((w[ent:t] > 0).sum())))
                if why != 'H': blocked = t + 63
        elif t > blocked and DD[t] and UP[t] and LEAD[t] and L3[t]: act = True; ent = t; pk = S[t]
    if act: log.append('%s..open(w-rows %d)' % (D[ent], int((w[ent:] > 0).sum())))
    print('  %-8s DD rows %d UP rows %d LEAD rows %d all-three rows %d | windows %d: %s' % (e['name'], int(DD.sum()), int(UP.sum()), int(LEAD.sum()), int((DD & UP & LEAD).sum()), len(log), ' '.join(log)))
