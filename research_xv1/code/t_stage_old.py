"""<= 2014 only: mechanics of the stage-A scoring and of a block-own account, with the stage-A calendar forced to end 2014-12-31.
Prints v1 / 1x / 3x per block on the liquidation-value basis (blocks 0-9, block 9 = 2013-14 only here) and, as a mechanics check,
the own-account figure of two old blocks next to their continuous-account figure."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
xv1.A_END = xv1.OLD_END
R = xv1._stage_a(xv1.ref); H1 = xv1._stage_a(xv1.hold1); H3 = xv1._stage_a(xv1.hold3)
for b in sorted(R):
    lv = xv1._levels(R[b])
    print('b%d %s %s n=%3d  v1 %+7.2f  1x %+7.2f  3x %+7.2f | mean level %.2f changes %3d in-block dd %6.1f%%' % (
        b, xv1.years_of(b), xv1.kind_of(b), len(R[b]['x']), 100 * xv1.ann([R[b]['x']]), 100 * xv1.ann([H1[b]['x']]), 100 * xv1.ann([H3[b]['x']]),
        lv['mean_level'], lv['changes'], 100 * lv['dd_inblock']))
for nm, bl in (('design', (1, 3, 5, 7, 9)), ('weak', xv1.WEAK)):
    a = [R[b]['x'] for b in bl]; h1 = [H1[b]['x'] for b in bl]; h3 = [H3[b]['x'] for b in bl]
    dA = [x - y for x, y in zip(a, h3)]; dB = [x - y for x, y in zip(a, h1)]
    print('%-6s n=%d v1 %+.2f 1x %+.2f 3x %+.2f | v1-3x %+.2f ci90 [%+.1f, %+.1f] t63 %.2f p %.3f | v1-1x %+.2f ci90 [%+.1f, %+.1f] t63 %.2f p %.3f | TE vs 1x %.1f%%' % (
        nm, sum(len(x) for x in a), 100 * xv1.ann(a), 100 * xv1.ann(h1), 100 * xv1.ann(h3), 100 * xv1.ann(dA), *[100 * z for z in xv1.ci90(dA)],
        xv1.test_t(dA, 63)[0], xv1.p_t(dA), 100 * xv1.ann(dB), *[100 * z for z in xv1.ci90(dB)], xv1.test_t(dB, 63)[0], xv1.p_t(dB), 100 * xv1.te_of(dB)))
X = xv1.frame(xv1.OLD_END); v = xv1.View(X); cal = xv1.Cal(xv1.acc_dates(X))
for mk, nm in ((xv1.ref, 'v1'), (xv1.hold3, '3x'), (xv1.hold1, '1x')):
    m = xv1._call(mk, v)
    print(nm, 'own-account vs continuous:', ' | '.join('b%d own %+.2f cont %+.2f' % (b, 100 * xv1.ann([xv1._block_account(v, m, cal, b)['x']]),
          100 * xv1.ann([xv1._stage_a(mk)[b]['x']])) for b in (5, 7, 8)))
