"""B1 conservative check: SGOV as a real traded product (0.3%/side cost on every idle-share change, full return = distribution taxed 15.4%).
mode all = every idle share in SGOV; mode deep = only the long-idle 2/3 chunk (L<=1 for 21 days), as etxeng sl_s085 'deep'."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as X
_o = X.product
def product(b, name, cash_kind='ms1'):
    if name == 'SGOV':
        f = b.rf; P, T = f.shape; d = np.maximum(f - 0.0009 / 252, 0.0); return d, np.zeros((P, T)), d, []
    return _o(b, name, cash_kind)
X.product = product
PR = ['TQQQ', 'SGOV', 'CASH']; out = {}
for sn, s in {'base': (2, .003), 'delay3': (3, .003), 'cost2x': (2, .006)}.items():
    for bn in ('dev250_path', 'real_ndx_86_14'):
        b = X.Basis(bn); L = X.s085_levels(bn, delay=s[0])
        ref = X.run(b, PR, [X.sl_s085(L)], [1.0], cost=s[1])
        for mode in ('all', 'deep'):
            r = X.row(X.run(b, PR, [X.sl_s085(L, fill={'SGOV': 1.0}, mode=mode)], [1.0], cost=s[1]), ref); r['v1'] = float(np.median(ref['cagr']))
            out['B1t_%s|%s|%s' % (mode, sn, bn)] = r
            print('B1t_%-4s %-7s %-15s cagr %.4f v1 %.4f d %+.4f pw %.2f dd80 %.2f' % (mode, sn, bn, r['cagr'], r['v1'], r['d_ref'], r['pw_ref'], r['dd80']), flush=True)
json.dump(out, open('/mnt/project-files/research/v1_states/results/b1_traded.json', 'w'), indent=1)
