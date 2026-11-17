"""<= 2014 only: mechanics of the design account (one continuous account on the calendar with the sealed rows removed).
The calendar ends 2014-12-31 and two OLD blocks (4 = 1998-2000 and 6 = 2004-06) play the sealed blocks, so that the join,
the embargo and the sealing can be exercised on rows that are not sealed in reality. Nothing here is a research result."""
import os
import sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1, t_world
t_world.old(); t_world.scratch('/tmp/xv1_t_design_acct'); FAKE = (4, 6)
X = xv1.frame(); cal = xv1.Cal(xv1.acc_dates(X))
plain = {mk.__name__: xv1._design_account(mk) for mk in (xv1.ref, xv1.hold3, xv1.hold1)}        # nothing removed: the plain continuous account
xv1.SEALED = FAKE; xv1._REF.clear()
spl = {mk.__name__: xv1._design_account(mk) for mk in (xv1.ref, xv1.hold3, xv1.hold1)}
print('1 blocks returned by the design account:', sorted(spl['ref']), '(the removed blocks are absent:', all(b not in spl['ref'] for b in FAKE), ')')
same = all(np.array_equal(spl[k][b][f], plain[k][b][f]) for k in spl for b in (0, 1, 2, 3) for f in ('x', 'lev', 'w', 'a0'))
print('2 blocks before the first removed block bit-identical to the plain account:', same)
# 3 sealing at the engine: whatever stands in the removed rows, the design account does not change
pre = xv1._prepare(xv1.ref); v, m = pre['v'], pre['m']; e = xv1._eng(v); base = xv1._run_eng(e, m, e.keep)
rm = np.setdiff1d(np.arange(e.T), e.keep); g = np.random.default_rng(1); bad = 0
for trial in range(3):
    e2 = xv1._eng(xv1._prepare(xv1.ref)['v']); m2 = dict(m)
    for nm, sd in (('r', 0.05), ('rf', 0.01)):
        a = getattr(e2, nm).copy(); a[rm] = g.normal(0, sd, len(rm)); setattr(e2, nm, a)
    f2 = e2.feat.copy(); f2[rm] = g.normal(0, 1, f2[rm].shape); e2.feat = f2
    for k in ('B', 'G', 'Wt', 'RB'):
        a = m[k].copy(); a[rm] = g.normal(0, 1, a[rm].shape); m2[k] = a
    bad += int(not np.array_equal(xv1._run_eng(e2, m2, e2.keep), base))
print('3 removed rows (%d) replaced by noise in r, rf, features, signal, weights: design account changed in %d of 3 trials' % (len(rm), bad))
# 4 the main account runs only inside an opening; the candidate's object carries neither the account kind nor the design rows
try: xv1._main_account(xv1.ref); print('4 ERROR: main account ran outside an opening')
except PermissionError as err: print('4 main account outside an opening refused:', err)
print('4 attributes of the object handed to candidate code:', sorted(k for k in vars(v)), '| keep / account on it:', hasattr(v, 'keep'), hasattr(v, 'account'))
# 5 how close is the spliced account to the true continuous one after a join (old blocks, v1): mechanics, not a result
for b in (5, 7, 8):
    a, c = spl['ref'][b], plain['ref'][b]
    print('5 b%d %s v1: growth spliced %+.2f plain %+.2f | level differs on %.0f%% of scored rows | mean level %.2f vs %.2f' % (
        b, xv1.years_of(b), 100 * xv1.ann([a['x']]), 100 * xv1.ann([c['x']]), 100 * np.mean(a['lev'] != c['lev']), a['lev'].mean(), c['lev'].mean()))
# 6 shadow levels of a design view: design-account levels on kept rows, full-calendar levels on removed rows
kd = e.keep[xv1.WARM:]; main = xv1._run_eng(e, m)
print('6 shadow: kept rows equal the design account:', np.array_equal(v.ref_target[kd], base[:, 2]),
      '| removed rows equal the full-calendar account:', np.array_equal(v.ref_target[rm], main[rm - xv1.WARM, 2]))
# 7 static-equivalent benchmark: holding more, less or something else on average has d* near 0, d far from 0
def tilt(w):
    def mk(vv):
        o = xv1.ref(vv); g3 = 3 * vv.c.r[0] - 2 * vv.c.rf[0] - 0.0245 / 252
        o.update(G=g3[:, None], Wt=np.full((vv.T, 1), w), mode=0, inc=0, RB=np.ones((vv.T, 1))); return o
    return mk
def capped(cap):
    def mk(vv):
        o = xv1.ref(vv); o['B'] = np.minimum(np.array(o['B'], dtype=float).reshape(-1), cap); return o
    return mk
def diluted(w):
    def mk(vv):
        o = xv1.ref(vv); g1 = vv.c.r[0] - 0.002 / 252
        o.update(G=g1[:, None], Wt=np.full((vv.T, 1), w), mode=1, inc=0, RB=np.ones((vv.T, 1))); return o
    return mk
R = spl['ref']; D = [b for b in (1, 3, 5, 7) if b in R]
for nm, mk in (('v1 + constant 10% in a second 3x fund', tilt(0.1)), ('v1 + constant 20% in a second 3x fund', tilt(0.2)), ('v1 capped at level 2', capped(2.0)),
               ('v1 capped at level 1', capped(1.0)), ('20% in the 1x index, v1 on the rest', diluted(0.2))):
    C = xv1._design_account(mk); d = xv1._paired(C, R, D); inf = {}; dn = xv1._neutral(C, R, D, None, inf)
    print('7 %-38s d %+6.2f  d* %+6.2f  (te %.1f, te* %.1f) | t63 %+.2f  t63* %+.2f | kappa %.2f delta0 %+.3f w %s' % (
        nm, 100 * xv1.ann(d), 100 * xv1.ann(dn), 100 * xv1.te_of(d), 100 * xv1.te_of(dn), xv1.test_t(d, 63)[0], xv1.test_t(dn, 63)[0],
        inf['kappa'], inf['delta0'], [round(x, 3) for x in inf['w']]))
# 8 sign-flip check
print('8 sign-flip p: 4 positive episodes %.4f (1/16 = 0.0625) | 8 positive %.4f (1/256 = 0.0039) | 20 mixed, all 2^20 assignments %.4f' % (
    xv1.p_sf([np.r_[np.zeros(63 * 16), np.tile(np.r_[1.0, np.zeros(62)], 4)]]), xv1.p_sf([np.tile(np.r_[1.0, np.zeros(62)], 8)]),
    xv1.p_sf([np.repeat(np.random.default_rng(3).normal(0.1, 1, 20), 63)])))
ep = np.r_[np.tile(np.r_[1.0, np.zeros(62)], 5), np.tile(np.r_[1e-9, np.zeros(62)], 15)]; rows = np.r_[np.tile(np.r_[True, np.zeros(62, dtype=bool)], 5), np.zeros(63 * 15, dtype=bool)]
print('8 five real episodes among 20 sub-blocks whose sums are not 0: p by non-zero sums %.4f | p by active sub-blocks %.4f (1/32 = 0.0313 > 1/60)' % (
    xv1.p_sf([ep]), xv1.p_sf([ep], 0, [rows])))
