"""<= 2014 only: mechanics of the design account (one continuous account on the calendar with the sealed rows removed).
The calendar ends 2014-12-31 and two OLD blocks (4 = 1998-2000 and 6 = 2004-06) play the sealed blocks, so that the join,
the embargo and the sealing can be exercised on rows that are not sealed in reality. Nothing here is a research result."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
xv1.CAL_END = xv1.A_END = xv1.OLD_END; FAKE = (4, 6)
X = xv1.frame(); cal = xv1.Cal(xv1.acc_dates(X))
plain = {mk.__name__: xv1._design_account(mk) for mk in (xv1.ref, xv1.hold3, xv1.hold1)}        # nothing removed: the plain continuous account
xv1.SEALED = FAKE
spl = {mk.__name__: xv1._design_account(mk) for mk in (xv1.ref, xv1.hold3, xv1.hold1)}
print('1 blocks returned by the design account:', sorted(spl['ref']), '(the removed blocks are absent:', all(b not in spl['ref'] for b in FAKE), ')')
same = all(np.array_equal(spl[k][b][f], plain[k][b][f]) for k in spl for b in (0, 1, 2, 3) for f in ('x', 'lev', 'w', 'a0'))
print('2 blocks before the first removed block bit-identical to the plain account:', same)
# 3 sealing at the engine: whatever stands in the removed rows, the design account does not change
v = xv1.View(X); m = xv1._call(xv1.ref, v); base = xv1._run(v, m, v.keep)
rm = np.setdiff1d(np.arange(v.T), v.keep); g = np.random.default_rng(1); bad = 0
for trial in range(3):
    v2 = xv1.View(X); m2 = dict(m)
    v2.c.r = v2.c.r.copy(); v2.c.rf = v2.c.rf.copy(); v2.c.r[0, rm] = g.normal(0, 0.05, len(rm)); v2.c.rf[0, rm] = g.normal(0, 0.01, len(rm))
    f2 = v.feat.copy(); f2[rm] = g.normal(0, 1, f2[rm].shape); v2._feat = f2
    for k in ('B', 'G', 'Wt', 'RB'):
        a = m[k].copy(); a[rm] = g.normal(0, 1, a[rm].shape); m2[k] = a
    bad += int(not np.array_equal(xv1._run(v2, m2, v2.keep), base))
print('3 removed rows (%d) replaced by noise in r, rf, features, signal, weights: design account changed in %d of 3 trials' % (len(rm), bad))
# 4 the main account needs the token
try: xv1._main_account(xv1.ref); print('4 ERROR: main account ran without the token')
except PermissionError as e: print('4 main account without the token refused:', e)
# 5 how close is the spliced account to the true continuous one after a join (old blocks, v1): mechanics, not a result
for b in (5, 7, 8):
    a, c = spl['ref'][b], plain['ref'][b]
    print('5 b%d %s v1: growth spliced %+.2f plain %+.2f | level differs on %.0f%% of scored rows | mean level %.2f vs %.2f' % (
        b, xv1.years_of(b), 100 * xv1.ann([a['x']]), 100 * xv1.ann([c['x']]), 100 * np.mean(a['lev'] != c['lev']), a['lev'].mean(), c['lev'].mean()))
# 6 shadow levels of a design view: design-account levels on kept rows, full-calendar levels on removed rows
kd = v.keep[xv1.WARM:]; main = xv1._run(v, m)
print('6 shadow: kept rows equal the design account:', np.array_equal(v.ref_target[kd], base[:, 2]),
      '| removed rows equal the full-calendar account:', np.array_equal(v.ref_target[rm], main[rm - xv1.WARM, 2]))
# 7 static-equivalent benchmark: a constant extra holding has d* near 0, d far from 0
def tilt(w):
    def mk(vv):
        o = xv1.ref(vv); g3 = 3 * vv.c.r[0] - 2 * vv.c.rf[0] - 0.0245 / 252
        o.update(G=g3[:, None], Wt=np.full((vv.T, 1), w), mode=0, inc=0, RB=np.ones((vv.T, 1))); return o
    return mk
R = spl['ref']; D = [b for b in (1, 3, 5, 7) if b in R]
for w in (0.1, 0.2):
    C = xv1._design_account(tilt(w)); d = xv1._paired(C, R, D); dn = xv1._neutral(C, R, D)
    print('7 v1 + constant %.0f%% in a second 3x fund (rebalanced daily, from idle cash): d %+.2f  d* %+.2f  (te %.1f, te* %.1f) | t63 %+.2f  t63* %+.2f' % (
        100 * w, 100 * xv1.ann(d), 100 * xv1.ann(dn), 100 * xv1.te_of(d), 100 * xv1.te_of(dn), xv1.test_t(d, 63)[0], xv1.test_t(dn, 63)[0]))
# 8 sign-flip check
print('8 sign-flip p: 4 positive episodes %.4f (1/16 = 0.0625) | 8 positive %.4f (1/256 = 0.0039) | 20 mixed %.3f' % (
    xv1.p_sf([np.r_[np.zeros(63 * 16), np.tile(np.r_[1.0, np.zeros(62)], 4)]]), xv1.p_sf([np.tile(np.r_[1.0, np.zeros(62)], 8)]),
    xv1.p_sf([np.repeat(np.random.default_rng(3).normal(0.1, 1, 20), 63)])))
