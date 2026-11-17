"""FRESH1 C2 (PREREG_C2_SGOV0.md): idle dollars in a short T-bill fund, re-measured with ZERO interest on idle cash.
Engine = research/v1_states/code/etxeng.py unchanged (account engine == MS1 std). <=2014 only."""
import os, sys, json
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/v1_states/code')
import etxeng as X
_o = X.product
def product(b, name, cash_kind='ms1'):
    f = b.rf; P, T = f.shape; zero = np.zeros((P, T))
    if name == 'SGOV':
        d = np.maximum(f - 0.0009 / 252, 0.0); return d, zero, d, []      # whole return = distribution, taxed 15.4%
    if name == 'CASH' and cash_kind == 'zero': return zero, zero, zero, []
    return _o(b, name, cash_kind)
X.product = product
def qqq1x(L):
    def f(p, J):
        lv = L[p]; K = lv.shape[0]; W = np.zeros((K, len(J))); lo = lv <= 1 + 1e-9
        W[:, J['TQQQ']] = np.where(lo, 0, lv / 3); W[:, J['QQQ']] = np.where(lo, lv, 0)
        W[:, J['CASH']] = 1 - W[:, J['TQQQ']] - W[:, J['QQQ']]
        return W, np.r_[True, np.any(np.diff(W, axis=0) != 0, axis=1)]
    return f
PR = ['TQQQ', 'QQQ', 'SGOV', 'CASH']; out = {}
SC = {'base': (2, .003, X.BASES), 'delay3': (3, .003, ['dev250_path', 'real_ndx_86_14']), 'cost2x': (2, .006, ['dev250_path', 'real_ndx_86_14']),
      'fee012_info': (2, .0012, ['dev250_path', 'real_ndx_86_14'])}
for sn, (dl, cost, bases) in SC.items():
    for bn in bases:
        b = X.Basis(bn); L = X.s085_levels(bn, delay=dl)
        if sn == 'base':
            chk = X.row(X.run(b, PR, [X.sl_s085(L)], [1.0], cost=cost))           # MS1 standard cash: parity check
            out['PARITY_ms1cash|%s' % bn] = chk
        ref = X.run(b, PR, [X.sl_s085(L)], [1.0], cost=cost, cash_kind='zero')
        out['REF0|%s|%s' % (sn, bn)] = X.row(ref)
        cands = {'DEEP': X.sl_s085(L, fill={'SGOV': 1.0}, mode='deep'), 'ALL': X.sl_s085(L, fill={'SGOV': 1.0}, mode='all'), 'QQQ1X': qqq1x(L)}
        for cn, sl in cands.items():
            r = X.row(X.run(b, PR, [sl], [1.0], cost=cost, cash_kind='zero'), ref)
            out['%s|%s|%s' % (cn, sn, bn)] = r
            print('%-6s %-11s %-15s cagr %.4f ref0 %.4f d %+.4f pw %.2f dd80 %.2f p10 %.4f tr %.1f' % (
                cn, sn, bn, r['cagr'], out['REF0|%s|%s' % (sn, bn)]['cagr'], r['d_ref'], r['pw_ref'], r['dd80'], r['p10'], r['tr']), flush=True)
        if sn == 'base': print('   parity (ms1 cash) %s %.4f' % (bn, out['PARITY_ms1cash|%s' % bn]['cagr']), flush=True)
def ok(c):
    g = lambda k: out['%s|%s' % (c, k)]
    r1 = g('base|dev250_path')['d_ref'] > 0 and g('base|dev250_path')['pw_ref'] > 0.5
    r2 = g('base|real_ndx_86_14')['cagr'] > out['REF0|base|real_ndx_86_14']['cagr']
    r3 = g('delay3|dev250_path')['d_ref'] >= 0 and g('cost2x|dev250_path')['d_ref'] >= 0
    return dict(rule1_path=bool(r1), rule2_real=bool(r2), rule3_stress=bool(r3), PASS=bool(r1 and r2 and r3))
out['VERDICT'] = {c: ok(c) for c in ('DEEP', 'ALL', 'QQQ1X')}
print(json.dumps(out['VERDICT']))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
