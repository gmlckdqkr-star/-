import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR'] = os.path.abspath('nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
ov = std.ov
def target(kind, c):
    B, bf, bp, fs = std.s085(c); B = B.copy(); v = c.vol(20); sh = ov.macro_cond(c, ('shock6m',))
    if kind in ('A1', 'A2'):
        lo = .30 if kind == 'A1' else .25; B = np.where((B == 3.0) & (v > lo) & (v <= .40), 2.0, B)
    elif kind == 'A3': B = np.where((B == 1.0) & (v > .40) & ~sh, 2.0, B)
    elif kind == 'A4': B = np.where((B == 1.0) & sh & ~(v > .40), 2.0, B)
    return B, bf, bp, fs
STRESS = {'base': {}, 'delay3': dict(delay=3), 'cost2x': dict(cost=0.006)}
C = std.contexts(); out = {}
for sn, kw in STRESS.items():
    for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85'):
        c = C[bn]; ref = std.engine(c, *target('base', c), **kw)[0]
        for k in ['A1', 'A2', 'A3', 'A4']:
            f, E = std.engine(c, *target(k, c), **kw); r, _ = std.row(f, E); d = f - ref
            r.update(v1=float(np.median(ref)), d=float(np.median(d)), pw=float(np.mean(d > 1e-5)))
            out['%s|%s|%s' % (k, sn, bn)] = r
            print('%s %-7s %-15s cagr %.4f v1 %.4f d %+.4f pw %.2f dd80 %s' % (k, sn, bn, r['cagr'], r['v1'], r['d'], r['pw'], r.get('dd80', '-')), flush=True)
json.dump(out, open('/mnt/project-files/research/v1_states/results/a_group.json', 'w'), indent=1)
