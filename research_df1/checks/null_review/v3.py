import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
R = json.load(open('/mnt/project-files/research/df1/checks/null/result.json')); EX = R['meta']['bond_excess_removed_per_day']['dev250_path']
MK = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85')
M = {bn: DC.market(bn) for bn in MK}
m0 = dict(M['dev250_path']); m0['rb'] = M['dev250_path']['rb'] - EX
def Lc(m, st, c, Lmax):
    L = np.where(st >= 3, float(c), np.where(st >= 1, min(float(c), Lmax / 3.0), 0.0)); return np.where(np.isnan(m['vol20']), 0.0, L)
def Lv(m, st, sig, Lmax):
    Lon = np.minimum(float(Lmax), sig / np.maximum(m['vol20'], 1e-9)); L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0)); return np.where(np.isnan(L), 0.0, L)
def run(m, L, knee, **kw):
    k = dict(RG.KNEES[knee]); k.update(vmode=0, roff=2, step_lo=0.1, step_hi=0.25); k.update(kw)
    o, _ = dfe.run(m, L, **k); cg, md = dfe.stats(o, m['r'].shape[1])
    if o.shape[0] > 1: return float(np.median(cg)), float(np.percentile(md, 10)), float(np.median(o[:, 8]))
    return float(cg[0]), float(md[0]), float(o[0, 8])
def full(Lf, knee):
    r = {bn: run(M[bn], Lf(M[bn]), knee) for bn in MK}
    wd = min(r[b][1] for b in MK[:3]); md = M['dev250_path']
    bx = run(m0, Lf(md), knee)[0]; c2 = run(md, Lf(md), knee, cost=0.006)[0]
    return '%.4f WD %.4f bx0 %.4f c2x %.4f lev %.2f | NDX %.4f/%.4f SPX29 %.4f/%.4f SPX55 %.4f/%.4f' % (r['dev250_path'][0], wd, bx, c2, r['dev250_path'][2],
        r['real_ndx_86_14'][0], r['real_ndx_86_14'][1], r['real_spx_29_54'][0], r['real_spx_29_54'][1], r['real_spx_55_85'][0], r['real_spx_55_85'][1])
print('T25 pick  ', full(lambda m: Lv(m, m['st_v1'], 0.1, 1.0), 'K1'), flush=True)
print('T30 pick  ', full(lambda m: Lv(m, m['st_v1'], 0.2, 1.0), 'K1'), flush=True)
for kn in ('K1', 'K2'):
    for c in (0.537, 0.6, 0.7, 0.75, 0.8, 0.9):
        print('v1 const %.3f %s' % (c, kn), full(lambda m: Lc(m, m['st_v1'], c, 1.0), kn), flush=True)
