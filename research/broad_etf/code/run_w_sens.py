"""BE1 after main run: (1) W variants (U_LONG + U_WIDE ACTUAL, real_ndx_86_14 only) for the path-best of F1, F2, F3;
(2) sensitivity (cost 2x, delay 3) of the overall path-best on all 5 bases. <=2014 only."""
import sys, json, numpy as np
import be1eng as G, bstrat as S, run_all as RA
OUT = '/mnt/project-files/research/broad_etf/results/'
res = json.load(open(OUT + 'main_le2014.json')); P = res['dev250_path']
cfg = dict(RA.CFG)
best = {f: max([n for n in P if n.startswith(f)], key=lambda n: P[n]['cagr']) for f in ('F1', 'F2', 'F3', 'F4')}
overall = max([n for n in P if n[:2] in ('F1', 'F2', 'F3', 'F4')], key=lambda n: P[n]['cagr'])
print('best per family', best, 'overall', overall)
out = {'best': best, 'overall': overall, 'W': {}, 'sens': {}}
bn = 'real_ndx_86_14'; bw = G.basis(bn, wide=True); bl = G.basis(bn)
ref = S.runspec(bl, S.S085(bl, bn))
for f in ('F1', 'F2', 'F3'):
    c = cfg[best[f]]
    xl = S.runspec(bl, RA.spec(bl, bn, c)); xw = S.runspec(bw, RA.spec(bw, bn, c))
    out['W'][best[f]] = dict(long=G.row(xl, ref), wide=G.row(xw, ref))
    print('W', best[f], 'long %.4f wide %.4f s085 %.4f' % (G.row(xl)['cagr'], G.row(xw)['cagr'], G.row(ref)['cagr']), flush=True)
c = cfg[overall]
for b_n in G.BASES:
    b = G.basis(b_n)
    for tag, kw in (('cost2x', dict(cost=0.006, delay=2)), ('delay3', dict(cost=0.003, delay=3))):
        r0 = S.runspec(b, S.S085(b, b_n, kw['delay']), cost=kw['cost'])
        x = S.runspec(b, RA.spec(b, b_n, c, kw['delay']), cost=kw['cost'])
        out['sens'].setdefault(b_n, {})[tag] = dict(cand=G.row(x, r0), s085=G.row(r0))
        print('SENS', b_n, tag, 'cand %.4f s085 %.4f d %.4f pw %.2f' % (G.row(x)['cagr'], G.row(r0)['cagr'], G.row(x, r0)['d_ref'], G.row(x, r0)['pw_ref']), flush=True)
    G._D.pop((b_n, False), None)
json.dump(out, open(OUT + 'w_sens_le2014.json', 'w'), indent=1)
