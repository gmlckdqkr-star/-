"""<= 2014 only: xeng with no extras must be bit-identical to beng.run1 (locked engine) for v1 and for 3x hold, standard and zero cash,
delay 2 and 3, cost x1 and x2. Also mechanical tests of the extras on synthetic numbers and of the 1x-hold instrument."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std, xeng
from std import bk, beng
X = xv1.frame(xv1.OLD_END); v = xv1.View(X); c = v.c; feat = v.feat
worst = 0
for nm, mk in (('v1', xv1.ref), ('3x', xv1.hold3)):
    m = xv1._call(mk, v)
    for kw in (dict(), dict(cspr=10.0), dict(cspr=10.0, delay=3), dict(cspr=10.0, delay=1), dict(cspr=10.0, cost=0.006), dict(cspr=10.0, tax=0.0), dict(cspr=10.0, W0=None)):
        k = dict(kw); k['fstep'] = m['fstep']
        _, a = beng.run_path(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), m['B'], feat, m['bfn'], m['bp'], **k)
        b = xeng.run(c.r[0], c.rf[0], m['B'], feat, m['bfn'], m['bp'], **k)
        d = int(np.sum(b[:, :4] != a[:, :4])); worst = max(worst, d)
        print('%-3s %-40s differing cells (equity, level, brake target, base) %d' % (nm, kw, d))
print('PARITY', 'OK (bit-identical)' if worst == 0 else 'FAIL', worst)
h = xv1._call(xv1.hold1, v); rec = xv1._run(v, h, 0, v.T)
lv = np.cumprod(1 + h['G'][xv1.WARM:, 0])
print('1x hold instrument: bought at close of day 2, never traded: equity / index ratio last day %.6f (expect %.6f = (1 - 0.003))' %
      (rec[-1, 0] / (lv[-1] / lv[2]), 1 - 0.003))
print('  liquidation value / equity last day %.4f (22%% tax on the gain above the first-year deduction)' % (rec[-1, 4] / rec[-1, 0]))
# synthetic mechanics: flat NDX (v1 base 0 -> all cash), one extra that doubles in a year, weight 20%, no tax, no cost
T = xeng.WARM + 600; r = np.zeros(T); rf = np.zeros(T); B = np.zeros(T); ft = np.zeros((T, bk.NF), np.float32)
G = np.zeros((T, 1)); G[xeng.WARM + 10:xeng.WARM + 262, 0] = 2 ** (1 / 252) - 1
W = np.zeros((T, 1)); W[xeng.WARM + 5:xeng.WARM + 300, 0] = 0.2
rec = xeng.run(r, rf, B, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=0, cspr=10.0, cost=0.0, tax=0.0, harvest=0)
print('synthetic: final equity %.6f (expect 1.2)  max extra weight %.4f' % (rec[-1, 0], rec[:, 5].max()))
rec = xeng.run(r, rf, B, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=0, cspr=10.0, cost=0.0, tax=0.22, harvest=0, W0=None)
print('synthetic with 22%% tax, no deduction: final equity %.6f  liquidation value %.6f (expect 1.156 both after the tax year)' % (rec[-1, 0], rec[-1, 4]))
# tranche semantics: three tranches of 10% each while the extra halves between them, then recovery x8; v1 off, no tax, no cost
G = np.zeros((T, 1)); W = np.zeros((T, 1)); a = xeng.WARM
W[a + 5:, 0] = 0.1; W[a + 50:, 0] = 0.2; W[a + 100:, 0] = 0.3; W[a + 400:, 0] = 0.0
G[a + 30, 0] = -0.5; G[a + 80, 0] = -0.5; G[a + 200, 0] = 7.0
rec = xeng.run(r, rf, B, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=0, inc=1, cspr=10.0, cost=0.0, tax=0.0, harvest=0)
# money in: 0.1 + 0.2*... tranche 2 = 0.1 of equity 0.95 ; tranche 3 = 0.1 of equity 0.9025 (approx)
e1 = 1.0; v = 0.1; cash = 0.9; v *= .5; e2 = v + cash; add = 0.1 * e2; v += add; cash -= add; v *= .5; e3 = v + cash; add = 0.1 * e3; v += add; cash -= add; v *= 8
print('tranche test: final equity %.6f (expect %.6f)' % (rec[-1, 0], v + cash))
# rebalancing rules of the extras (flat NDX, no cost, no tax, no fund drag): exact expectations
a = xeng.WARM; z = dict(cspr=10.0, cost=0.0, tax=0.0, harvest=0, er3=0.0)
B3 = np.full(T, 3.0); W = np.full((T, 1), 0.1)
G = np.zeros((T, 1)); G[a + 50, 0] = 1.0
rec = xeng.run(r, rf, B3, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=1, up=[0.5], **z)
print('band skim  : weight day 51 %.4f (expect 0.1818), day 52 %.4f (expect 0.1000), equity %.4f (expect 1.1)' % (rec[51, 5], rec[52, 5], rec[-1, 0]))
rec = xeng.run(r, rf, B3, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=1, **z)
print('no band    : weight last day %.4f (expect 0.1818)' % rec[-1, 5])
RB = np.zeros((T, 1)); RB[a + 100, 0] = 1
rec = xeng.run(r, rf, B3, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=1, RB=RB, **z)
print('flag       : weight day 101 %.4f (expect 0.1818), day 102 %.4f (expect 0.1000)' % (rec[101, 5], rec[102, 5]))
G = np.zeros((T, 1)); G[a + 50, 0] = -0.6
rec = xeng.run(r, rf, B3, ft, std.ident, np.zeros(1), G=G, Wt=W, mode=1, dn=[0.5], **z)
print('band refill: weight day 51 %.4f (expect 0.0426), day 52 %.4f (expect 0.1000), equity %.4f (expect 0.94)' % (rec[51, 5], rec[52, 5], rec[-1, 0]))
Bs = np.full(T, 3.0); Bs[a + 100:a + 200] = 0.0; W2 = np.full((T, 1), 0.2)
rec = xeng.run(r, rf, Bs, ft, std.ident, np.zeros(1), G=np.zeros((T, 1)), Wt=W2, mode=0, **z)
print('mode 0     : weight while v1 is at 3x %.4f (expect 0), while v1 is in cash %.4f (expect 0.2), after v1 returns %.4f (expect 0)' % (rec[60, 5], rec[150, 5], rec[260, 5]))
