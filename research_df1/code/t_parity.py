"""Parity: dfe (vmode 1 = TQQQ L/3 + cash) vs locked MS1 engine std.engine (beng.run1) on the same decision path."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, std
res = {}
for bn in ('real_ndx_86_14', 'dev250_path', 'real_spx_55_85', 'real_spx_29_54', 'JP'):
    m = DC.market(bn); c = m['ctx']; B = m['st_v1'].astype(float)
    for tag, BB, fs in (('v1B_step05', B, 0.5), ('halfB_fstep01', 0.5 * B, 0.1), ('v1B_al_fstep01', m['st_al'] * 0.7, 0.1)):
        cg, E = std.engine(c, BB, std.ident, np.zeros(1), fs, cspr=10.0)
        o, _ = dfe.run(m, BB, vmode=1, step_hi=0.5, step_lo=fs, roff=0, kon=0)
        cg2, md2 = dfe.stats(o, m['r'].shape[1])
        md1 = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
        d = float(np.max(np.abs(cg - cg2))); dm = float(np.max(np.abs(md1 - md2)))
        res['%s|%s' % (bn, tag)] = dict(max_abs_cagr_diff=d, max_abs_mdd_diff=dm, cagr_med=float(np.median(cg)))
        print(bn, tag, 'cagr diff %.2e mdd diff %.2e med %.4f' % (d, dm, np.median(cg)), flush=True)
json.dump(res, open('/mnt/project-files/research/df1/results/parity.json', 'w'), indent=1)
print('MAX', max(v['max_abs_cagr_diff'] for v in res.values()), max(v['max_abs_mdd_diff'] for v in res.values()))
