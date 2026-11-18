import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
MK = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85')
M = {bn: DC.market(bn) for bn in MK}
def Lc(m, st, c, Lmax):
    Lon = np.full(st.shape, float(c)); L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0))
    L = np.where(np.isnan(m['vol20']), 0.0, L); return L
def run(m, L, knee, **kw):
    k = dict(RG.KNEES[knee]); k.update(vmode=0, roff=2, step_lo=0.1, step_hi=0.25); k.update(kw)
    o, _ = dfe.run(m, L, **k); cg, md = dfe.stats(o, m['r'].shape[1])
    if o.shape[0] > 1: return float(np.median(cg)), float(np.percentile(md, 10)), float(np.median(o[:, 4]))
    return float(cg[0]), float(md[0]), float(o[0, 4])
for knee, Lmax in (('K1', 1.0), ('K2', 1.0)):
  for c in (0.4, 0.5, 0.537, 0.6, 0.7):
    for lab, stf in (('v1', lambda m: m['st_v1']), ('on', lambda m: np.full(m['r'].shape, 3.0))):
        r = {bn: run(M[bn], Lc(M[bn], stf(M[bn]), c, Lmax), knee) for bn in MK}
        wd = min(r[b][1] for b in MK[:3])
        print('%s const %.3f %-3s path %.4f WD %.4f | NDX %.4f/%.4f SPX29 %.4f/%.4f SPX55 %.4f/%.4f ntr %.0f' % (knee, c, lab, r['dev250_path'][0], wd,
              r['real_ndx_86_14'][0], r['real_ndx_86_14'][1], r['real_spx_29_54'][0], r['real_spx_29_54'][1], r['real_spx_55_85'][0], r['real_spx_55_85'][1], r['dev250_path'][2]), flush=True)
