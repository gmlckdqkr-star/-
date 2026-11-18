"""E4 support (report-only): friction decomposition of the top config under Sharpe parity (N4, k=1). <=2014 data only."""
import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, df5run as R
idx = {c['id']: c for c in D6.configs()}
TOP = idx['L|TQQQ|DEF3|R252|e0.60|c0.80']
out = {}
for wname in ('P', 'X'):
    X = D6.W6(wname, 'N4', None, ['DEF3'])
    d3, inc, hv = X.pan['DEF3']; tq = X.pan['TQQQ']
    X.pan['DEF3_fl'] = (d3 + D6.ER / 252, 0.0, 1)                 # no expense ratio, no dividend income taxed
    X.pan['TQQQ_fl'] = (tq[0] + 0.0245 / 252, 0.0, 1)             # 3r - 2rf, no fee
    for nm, over, sl, lev in (('N4_base', {}, 'DEF3', 'TQQQ'), ('N4_noCGT', dict(tax=0.0), 'DEF3', 'TQQQ'),
                              ('N4_noCGT_nocost', dict(tax=0.0, cost=0.0), 'DEF3', 'TQQQ'),
                              ('N4_frictionless', dict(tax=0.0, cost=0.0), 'DEF3_fl', 'TQQQ_fl')):
        qcg, qmd, _ = D6.bench(X, None, **over)
        c = dict(TOP, S=sl)
        if lev != 'TQQQ':
            X.pan['TQQQ_orig'] = X.pan['TQQQ']; X.pan['TQQQ'] = X.pan[lev]
        cg, md, _ = D6.run(c, X, None, **over)
        if lev != 'TQQQ': X.pan['TQQQ'] = X.pan['TQQQ_orig']
        s = R.summ(cg, md, qcg); q = R.summ(qcg, qmd)
        out.setdefault(nm, {})[wname + '30'] = dict(pair=s['pair'], med_ex=s['cagr'] - q['cagr'], qqq=q['cagr'],
                                                     ddm=1 - abs(s['mdd_p10']) / abs(q['mdd_p10']))
        print(wname, nm, {k: round(v, 4) for k, v in out[nm][wname + '30'].items()}, flush=True)
    del X; D6.drop(wname)
json.dump(out, open('/tmp/df6v/limit/e4.json', 'w'), indent=1)
