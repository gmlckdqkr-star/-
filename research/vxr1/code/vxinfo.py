"""Post-hoc INFO only (not a pass test): G1/G2 via a non-PTP route (futures), all other stresses at once; ACTUAL sub-windows."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vxrun as R, uprun as U, updata as UD
SEED = 20261112; ALL = dict(cut=0.50, cmul=2.0, fee_add=0.01, rf_on=False)
def win(res_, a, b, bn='real_ndx_86_14'):
    c = U.basis(bn)['c']; dates, X = UD.basis_dates()[bn]; d = dates[c.ii[0, R.WARM:]]; C = res_['curve'][0]
    i0 = int(np.searchsorted(d, pd.Timestamp(a))) - 1; i1 = int(np.searchsorted(d, pd.Timestamp(b), side='right')) - 1
    return float((C[i1] / C[i0]) ** (252 / (i1 - i0)) - 1)
out = {}
refp = R.run('dev250_path', None, 0.0, cmul=2.0); refr = R.run('real_ndx_86_14', None, 0.0, cmul=2.0); ref0 = R.run('real_ndx_86_14', None, 0.0)
for g in ('G1', 'G2'):
    for s in (0.10, 0.20):
        nm = '%s_s%02d' % (g, int(s * 100)); x = R.run('dev250_path', g, s, inject=(10, SEED), **ALL); rw = U.row(x, refp)
        ds = []; da = []
        for sd in range(SEED, SEED + 200):
            y = R.run('real_ndx_86_14', g, s, inject=(10, sd), **ALL); ds.append(y['cagr'][0] - refr['cagr'][0]); da.append(R.actual_window(y)[0] - R.actual_window(refr)[0])
        xb = R.run('real_ndx_86_14', g, s)
        out[nm] = dict(path_d=rw['d_ref'], path_pw=rw['pw_ref'], path_cagr=rw['cagr'], real_d_med=float(np.median(ds)), act_d_med=float(np.median(da)),
                       base_d_2006_14=win(xb, '2006-01-01', '2014-12-31') - win(ref0, '2006-01-01', '2014-12-31'),
                       base_d_2011_14=win(xb, '2011-01-01', '2014-12-31') - win(ref0, '2011-01-01', '2014-12-31'))
        print(nm, {k: round(100 * v, 2) for k, v in out[nm].items()}, flush=True)
json.dump(out, open('/mnt/project-files/research/vxr1/results/info_posthoc_le2014.json', 'w'), indent=1)
