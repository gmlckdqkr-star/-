"""FINAL1 lane NBR (PRECOMMIT_FINAL1 section 2): split the account across neighbouring v1 parameters. <=2014 only.
Each sub-account = fam4(c, 3.0, vcap, 1.0, caution=('shock6m',), Lc=1.0, sl=sl, band=.02) + av23s(.85), own tax book, equal start, never
rebalanced across sub-accounts. Combined after-tax final = mean of sub-account finals; MDD from the mean equity curve."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, bk, ce, rx
CM, ov, S = bk._co()
OUT = '/mnt/project-files/research/final1/results/'
SETS = {'NBR5': [(200, .40), (180, .40), (220, .40), (200, .35), (200, .45)],
        'NBR9': [(sl, v) for sl in (180, 200, 220) for v in (.35, .40, .45)]}
t0 = time.time(); res = {}; cache = {}
def sub(bn, c, sl, v, kw):
    key = (bn, sl, v, tuple(sorted(kw.items())))
    if key not in cache:
        B = S.fam4(c, 3.0, v, 1.0, caution=('shock6m',), Lc=1.0, sl=sl, band=0.02)
        f, E = std.engine(c, B, rx.av23s, rx.P_av23s(.85), 0.1, **kw)
        cache[key] = (f, E)
    return cache[key]
for tag, kw in (('base', {}), ('delay3', dict(delay=3)), ('cost2x', dict(cost=0.006))):
    for nm, pts in SETS.items():
        out = {}
        for bn, c in std.contexts().items():
            yrs = (c.r.shape[1] - ov.WARM) / 252
            fr, Er = sub(bn, c, 200, .40, kw)                       # v1 itself under the same terms
            if tag == 'base':
                rB, rbf, rbp, rfs = std.s085(c); f0, _ = std.engine(c, rB, rbf, rbp, rfs)
                assert np.max(np.abs(f0 - fr)) < 1e-12, 'centre point must equal v1'
            fins = []; EE = 0
            for sl, v in pts:
                f, E = sub(bn, c, sl, v, kw); fins.append((1 + f) ** yrs); EE = EE + E / len(pts)
            fin = np.mean(fins, axis=0); cg = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
            row, _ = std.row(cg, EE); d = cg - fr
            row.update(d_vs_v1=float(np.median(d)), pw_vs_v1=float(np.mean(d > 1e-5)), v1=float(np.median(fr)),
                       sub_cagr={('%d_%.2f' % p): float(np.median(sub(bn, c, p[0], p[1], kw)[0])) for p in pts})
            out[bn] = row
        res['%s|%s' % (nm, tag)] = out
        print('%-5s %-7s path %.4f (d %+.4f pw %.2f dd80 %.2f) real %.4f (d %+.4f) spx55 %.4f (d %+.4f) spx70 %.4f (d %+.4f)' % (
            nm, tag, out['dev250_path']['cagr'], out['dev250_path']['d_vs_v1'], out['dev250_path']['pw_vs_v1'], out['dev250_path']['dd80'],
            out['real_ndx_86_14']['cagr'], out['real_ndx_86_14']['d_vs_v1'], out['real_spx_55_85']['cagr'], out['real_spx_55_85']['d_vs_v1'],
            out['real_spx_70_85']['cagr'], out['real_spx_70_85']['d_vs_v1']), flush=True)
b5, b9 = res['NBR5|base'], res['NBR9|base']
ok = lambda b: bool(b['dev250_path']['d_vs_v1'] > 0.003 and b['dev250_path']['pw_vs_v1'] >= 0.55 and b['real_ndx_86_14']['d_vs_v1'] > 0)
res['PASS'] = dict(NBR5=ok(b5), NBR9=ok(b9), both_path_positive=bool(b5['dev250_path']['d_vs_v1'] > 0 and b9['dev250_path']['d_vs_v1'] > 0))
print('sub-account medians path', b9['dev250_path']['sub_cagr']); print('sub-account real', b9['real_ndx_86_14']['sub_cagr'])
print('PASS', res['PASS'], '%.0fs' % (time.time() - t0))
json.dump(res, open(OUT + 'nbr.json', 'w'), indent=1, default=float)
