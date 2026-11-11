"""<= 2014 only: the evaluator's account must equal the locked standard on the old calendar (no post-2014 day is touched)."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std
c, dates = xv1.build(xv1.OLD_END); cal = xv1.Cal(dates)
print('days', len(dates), dates[0].date(), dates[-1].date(), 'blocks', cal.blocks)
rec = xv1.account(c, std.s085)
fin, EE = std.engine(c, *std.s085(c), cspr=10.0)
print('std zero-interest real NDX 86-14 CAGR after liquidation tax: %.4f%% (record 30.53)' % (100 * fin[0]))
print('run_path vs runPE equity: max abs rel diff %.3e' % np.max(np.abs(rec[:, 0] / EE[0] - 1)))
fin0, _ = std.engine(c, *std.s085(c))
print('std standard cash (rf-2pp) CAGR: %.4f%% (record 31.08)' % (100 * fin0[0]))
x = xv1.xlog(rec[:, 0], cal); h1 = xv1.hold1_x(c, cal); x3 = xv1.xlog(xv1.account(c, xv1.hold3)[:, 0], cal)
print('embargo check: first scored rank', int(cal.rank[cal.scored].min()), '| scored days', int(cal.scored.sum()), 'of', cal.n)
for row, r1, r3 in zip(xv1.table(x, cal), xv1.table(h1, cal), xv1.table(x3, cal)):
    print('b%-2d %s %s n=%3d  v1 %+7.2f  1x %+7.2f  3x %+7.2f' % (row['block'], row['years'], row['kind'], row['n'], 100 * row['ann'], 100 * r1['ann'], 100 * r3['ann']))
for nm, o in xv1.sets(x, cal).items():
    print(nm, o['n'], '%.2f' % (100 * o['ann']), '| 1x %.2f | 3x %.2f' % (100 * xv1.sets(h1, cal)[nm]['ann'], 100 * xv1.sets(x3, cal)[nm]['ann']))
