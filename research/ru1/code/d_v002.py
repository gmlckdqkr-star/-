"""D2/D3: V002 as a real user could run it. Cash 0 and no year-end harvest on every row (app conditions), MS1 costs/tax.
Rows: v1; V002 as researched (21-day band); V002 without periodic rebalancing (app 1.0.2 has none); V002 investable
(VALPROF4 -> S&P 500 1x, CAPE_L3 -1%/yr product drag) with / without band. <=2014 only."""
import os, sys, json
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/v002/code')
import std, grid as G
import ii, el
el.CSPR = 10.0
jv = ii.SID.index('VALPROF4_L1'); jc = ii.SID.index('CAPE_L3'); js = ii.SID.index('SPXH_L1')
def run(bn, sleeves, rebal=True):
    S, SO = ii.arrays(bn); TQ, DEP, CU, IDL = ii._REFIN[bn]
    if not sleeves:
        Sa = np.zeros(S.shape[:2] + (1,), S.dtype); SOa = np.zeros_like(Sa); wa = np.zeros(1); a0 = 1.0
    else:
        cols = []; socols = []; w = []
        for j, wt, extra in sleeves:
            cols.append(S[:, :, j].astype(np.float64) - extra / 252); socols.append(SO[:, :, j]); w.append(wt)
        Sa = np.ascontiguousarray(np.stack(cols, 2).astype(S.dtype)); SOa = np.ascontiguousarray(np.stack(socols, 2)); wa = np.array(w, float); a0 = 1 - wa.sum()
    fin, E = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                      float(a0), np.ascontiguousarray(wa), 0, 0.003, ii._PP['tax'], ii._D, 0, ii._PP['hthr'], 21 if rebal else 10 ** 9, 0.05, 0.25)
    y = E.shape[1] / 252
    return np.maximum(fin, 1e-9) ** (1 / y) - 1, E
def st(cg, E, ref=None):
    m = (E / np.maximum.accumulate(E, 1) - 1).min(1)
    o = dict(p50=float(np.median(cg)), mdd_med=float(np.median(m)))
    if len(cg) > 1: o.update(p10=float(np.percentile(cg, 10)), dd80=float(np.mean(m <= -.8)))
    if ref is not None: d = cg - ref; o.update(d_med=float(np.median(d)), p_beat=float(np.mean(d > 1e-6)))
    return o
V = {'V002_researched': ([(jv, .15, .006), (jc, .10, 0.0)], True), 'V002_no_rebalance': ([(jv, .15, .006), (jc, .10, 0.0)], False),
     'V002i_SP500_band': ([(js, .15, 0.0), (jc, .10, 0.01)], True), 'V002i_SP500_no_rebalance': ([(js, .15, 0.0), (jc, .10, 0.01)], False)}
res = {}
for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85'):
    ii._REFIN[bn] = el.ref_inputs(el.ctx(bn))   # brake model as the app (model cash rf-2%); account cash 0 via el.CSPR (verifier fix 11-12)
    v, Ev = run(bn, []); res[bn] = {'v1': st(v, Ev)}
    for nm, (sl_, rb) in V.items():
        g, E = run(bn, sl_, rb); res[bn][nm] = st(g, E, v)
    ii._ARR.clear()
    print(bn, json.dumps(res[bn]), flush=True)
json.dump(res, open('/mnt/project-files/research/ru1/results/d_v002.json', 'w'), indent=1)
