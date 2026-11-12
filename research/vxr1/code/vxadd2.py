"""ADDENDUM 2: all-stress-at-once rows for G0 passers + ACTUAL sub-windows -> results/add2_le2014.json"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vxrun as R, uprun as U, updata as UD
OUT = '/mnt/project-files/research/vxr1/results/add2_le2014.json'; SEED = 20261112
ALL = dict(cut=0.50, cmul=2.0, fee_add=0.01, rf_on=False, ptp=0.10)
res = {}
def win(res_, a, b, bn='real_ndx_86_14'):
    c = U.basis(bn)['c']; dates, X = UD.basis_dates()[bn]; d = dates[c.ii[0, R.WARM:]]; C = res_['curve'][0]
    i0 = int(np.searchsorted(d, pd.Timestamp(a))) - 1; i1 = int(np.searchsorted(d, pd.Timestamp(b), side='right')) - 1
    return float((C[i1] / C[i0]) ** (252 / (i1 - i0)) - 1)
for s in (0.10, 0.20):
    nm = 'G0_s%02d' % int(s * 100); row = {}
    for yrs in (10, 5):
        refp = R.run('dev250_path', None, 0.0, cmul=2.0)
        x = R.run('dev250_path', 'G0', s, inject=(yrs, SEED), **ALL); rw = U.row(x, refp)
        row['path_all_inj%d' % yrs] = dict(cagr=rw['cagr'], v1=U.row(refp)['cagr'], d=rw['d_ref'], pw=rw['pw_ref'], dd80=rw['dd80'], v1_dd80=U.row(refp)['dd80'], p10=rw['p10'])
        refr = R.run('real_ndx_86_14', None, 0.0, cmul=2.0); ds = []; da = []
        for sd in range(SEED, SEED + 200):
            x = R.run('real_ndx_86_14', 'G0', s, inject=(yrs, sd), **ALL)
            ds.append(x['cagr'][0] - refr['cagr'][0]); da.append(R.actual_window(x)[0] - R.actual_window(refr)[0])
        row['real_all_inj%d' % yrs] = dict(d_med=float(np.median(ds)), d_pw=float(np.mean(np.array(ds) > 0)), act_d_med=float(np.median(da)), act_pw=float(np.mean(np.array(da) > 0)),
                                         v1=float(refr['cagr'][0]), v1_act=R.actual_window(refr)[0])
    ref = R.run('real_ndx_86_14', None, 0.0); x = R.run('real_ndx_86_14', 'G0', s)
    row['act_windows_base'] = {k: dict(v1=win(ref, a, b), cand=win(x, a, b), d=win(x, a, b) - win(ref, a, b)) for k, (a, b) in
                               {'2006-2014': ('2006-01-01', '2014-12-31'), '2006-2010': ('2006-01-01', '2010-12-31'), '2011-2014': ('2011-01-01', '2014-12-31')}.items()}
    res[nm] = row; json.dump(res, open(OUT, 'w'), indent=1)
    print(nm, json.dumps(row, indent=0), flush=True)
