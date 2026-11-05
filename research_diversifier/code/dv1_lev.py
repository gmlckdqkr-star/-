"""DV1 side question (user 00:54Z): VALPROF4 levered L in {1,1.5,2,3} standalone under MS1, vintage drag 0.6%/yr, synthetic lever cost as MS1 (L*r-(L-1)rf-2.45%/yr).
No buyable leveraged value+profitability product exists in the universe -> theoretical. <=2014."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el
j = ii.SID.index('VALPROF4_L1'); out = {}
for bn in ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']:
    TQ, DEP, CU, IDL = ii.ref_in(bn); S, SO = ii.arrays(bn); rf = np.asarray(el.ctx(bn)['rf'])[:, ii.WARM:]
    base = S[:, :, j].astype(np.float64) + ii.VPF_COST - 0.006 / 252
    for L in (1.0, 1.5, 2.0, 3.0):
        s = L * base - ii.VPF_COST * L - (0 if L == 1 else (L - 1) * rf + 0.0245 / 252)
        Sa = np.ascontiguousarray(s[:, :, None].astype(S.dtype)); SOa = np.ascontiguousarray(SO[:, :, j:j + 1])
        for w in (1.0, 0.3):
            fin, E = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                              1 - w, np.array([w]), 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
            r = ii.stats(bn, fin, E)
            out['%s|L%.1f|w%.1f' % (bn, L, w)] = {k: float(r[k]) for k in ('cagr', 'mdd', 'dd80') if k in r}
            print(bn, L, w, {k: round(float(r[k]), 3) for k in ('cagr', 'mdd', 'dd80') if k in r}, flush=True)
json.dump(out, open('/mnt/project-files/research/diversifier/results/valprof4_lev.json', 'w'), indent=1)
