"""<= 2014 only: xeng with no extras must equal beng.run1 (locked engine) for v1 and for 3x hold, standard and zero cash,
delay 2 and 3, cost x1 and x2. Also a mechanical test of the extras on synthetic numbers."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std, xeng
from std import bk, beng
c, dates = xv1.build(xv1.OLD_END)
feat = bk.features(c)[0]
worst = 0.0
for nm, mk in (('v1', std.s085), ('3x', xv1.hold3)):
    m = mk(c)
    for kw in (dict(), dict(cspr=10.0), dict(cspr=10.0, delay=3), dict(cspr=10.0, cost=0.006)):
        k = dict(kw); k['fstep'] = m[3]
        _, a = beng.run_path(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), np.ascontiguousarray(m[0][0], dtype=np.float64),
                             np.ascontiguousarray(feat), m[1], np.asarray(m[2], dtype=np.float64), **k)
        b = xeng.run(c.r[0], c.rf[0], m[0][0], feat, m[1], m[2], **k)
        d = float(np.max(np.abs(b[:, 0] / a[:, 0] - 1))); dl = float(np.max(np.abs(b[:, 1] - a[:, 1]))); worst = max(worst, d, dl)
        print('%-3s %-32s equity max rel diff %.2e  level max diff %.1e' % (nm, kw, d, dl))
print('PARITY', 'OK' if worst < 1e-12 else 'FAIL', worst)
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
