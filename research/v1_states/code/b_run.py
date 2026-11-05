"""VS1 B group: v1 in-force levels L (brake from v1's own path) with state-specific products. etxeng account engine (== MS1 std)."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as X
BASES = ['dev250_path', 'real_ndx_86_14']
def prod_extra(b, name):
    f = b.rf; P, T = f.shape; zero = np.zeros((P, T))
    if name == 'SPY': return b.z('U_SPX') - 0.0009 / 252, zero, np.full((P, T), 0.018 / 252), ['U_SPX']
    if name == 'IAU': return b.z('GLD') - 0.0025 / 252, zero, zero, ['GLD']
    if name == 'PSQ': return -b.rN + f - 0.017 / 252, zero, zero, []
    return None
_orig = X.product
def product(b, name, cash_kind='ms1'):
    r = prod_extra(b, name)
    return r if r is not None else _orig(b, name, cash_kind)
X.product = product
def sleeve(L, kind):
    def f(p, J):
        lv = L[p]; K = lv.shape[0]; W = np.zeros((K, len(J))); lo = lv <= 1 + 1e-9; zero = lv <= 1e-9
        if kind in ('base', 'B1'):
            W[:, J['TQQQ']] = lv / 3; W[:, J['CASH']] = 1 - lv / 3
        elif kind in ('B2', 'B3'):
            a = 'QQQ' if kind == 'B2' else 'SPY'
            W[:, J['TQQQ']] = np.where(lo, 0, lv / 3); W[:, J[a]] = np.where(lo, lv, 0)
            W[:, J['CASH']] = 1 - W[:, J['TQQQ']] - W[:, J[a]]
        elif kind in ('B4', 'B5'):
            a = 'IAU' if kind == 'B4' else 'PSQ'
            W[:, J['TQQQ']] = lv / 3; W[:, J[a]] = np.where(zero, 1.0, 0.0); W[:, J['CASH']] = 1 - W[:, J['TQQQ']] - W[:, J[a]]
        fl = np.r_[True, np.any(np.diff(W, axis=0) != 0, axis=1)]
        return W, fl
    return f
PRODS = ['TQQQ', 'QQQ', 'SPY', 'IAU', 'PSQ', 'CASH']
def main():
    STRESS = {'base': dict(delay=2, cost=0.003), 'delay3': dict(delay=3, cost=0.003), 'cost2x': dict(delay=2, cost=0.006)}
    kinds = sys.argv[1].split(',') if len(sys.argv) > 1 else ['B1', 'B2', 'B3', 'B4', 'B5']
    out = {}
    for sn, s in STRESS.items():
        for bn in BASES:
            b = X.Basis(bn); L = X.s085_levels(bn, delay=s['delay'])
            ref = X.run(b, PRODS, [sleeve(L, 'base')], [1.0], cost=s['cost'])
            rr = X.row(ref)
            if sn == 'base': print('v1 %-7s %-15s cagr %.4f' % (sn, bn, rr['cagr']), flush=True)
            for k in kinds:
                if k == 'B6': continue
                res = X.run(b, PRODS, [sleeve(L, k)], [1.0], cost=s['cost'], cash_kind=('sgov' if k == 'B1' else 'ms1'))
                r = X.row(res, ref); r['v1'] = rr['cagr']
                for n in ('GLD', 'U_SPX'):
                    if (k == 'B4' and n == 'GLD') or (k == 'B3' and n == 'U_SPX'): r['cover_' + n] = b.cover(n)
                out['%s|%s|%s' % (k, sn, bn)] = r
                print('%s %-7s %-15s cagr %.4f v1 %.4f d %+.4f pw %.2f dd80 %.2f tr %.1f %s' % (k, sn, bn, r['cagr'], r['v1'], r['d_ref'], r['pw_ref'], r['dd80'], r['tr'], {a: round(v, 3) for a, v in r.items() if a.startswith('cover')}), flush=True)
    json.dump(out, open('/mnt/project-files/research/v1_states/results/b_group.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
