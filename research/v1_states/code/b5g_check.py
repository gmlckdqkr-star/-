"""Post-hoc (user follow-up 11-05 10:03Z): PSQ / IAU only while the C3 crisis gate itself says 0 (not brake-induced zeros). N +2."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import b_run as BR
X = BR.X
out = {}
for sn, (dl, cost) in {'base': (2, .003), 'delay3': (3, .003), 'cost2x': (2, .006)}.items():
    for bn in BR.BASES:
        b = X.Basis(bn); L = X.s085_levels(bn, delay=dl); c = b.c
        B = X.std.s085(c)[0]; W = X.WARM; T = c.T
        g0 = (B[:, W - dl:T - dl] == 0)          # gate decision in force on the same row as L
        ref = X.run(b, BR.PRODS, [BR.sleeve(L, 'base')], [1.0], cost=cost)
        for a in ('PSQ', 'IAU'):
            def f(p, J, a=a):
                lv = L[p]; K = lv.shape[0]; Wt = np.zeros((K, len(J))); z = g0[p] & (lv <= 1e-9)
                Wt[:, J['TQQQ']] = lv / 3; Wt[:, J[a]] = np.where(z, 1.0, 0.0); Wt[:, J['CASH']] = 1 - Wt[:, J['TQQQ']] - Wt[:, J[a]]
                return Wt, np.r_[True, np.any(np.diff(Wt, axis=0) != 0, axis=1)]
            r = X.row(X.run(b, BR.PRODS, [f], [1.0], cost=cost), ref); r['v1'] = float(np.median(ref['cagr'])); r['gate_share'] = float(np.mean(g0))
            out['%s_gate|%s|%s' % (a, sn, bn)] = r
            print('%s_gate %-7s %-15s cagr %.4f v1 %.4f d %+.4f pw %.2f dd80 %.2f gate %.3f' % (a, sn, bn, r['cagr'], r['v1'], r['d_ref'], r['pw_ref'], r['dd80'], r['gate_share']), flush=True)
json.dump(out, open('/mnt/project-files/research/v1_states/results/b5g_gate_only.json', 'w'), indent=1)
