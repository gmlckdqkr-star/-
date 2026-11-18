"""Structural sweep (post-hoc): pre-tax, daily-rebalanced static mixes on the X30 paths: NDX exposure n (+0.55%/yr div) + sleeve weight d,
rest at rf (negative = borrowing). Financing spread on borrowed amount: 0 (frictionless) or 1.225%/yr (TQQQ fee per extra unit) [+0.55% if TQQQ dividend missing].
Compared with frictionless QQQ on the same paths. Neutralized and raw panels."""
import os, sys, json, itertools
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5run as R, df5lib as L, df5data as DD
WARM = 300; DQ = 0.0055
def perf(dr):
    lw = np.cumsum(np.log1p(dr), axis=1); lw = np.c_[np.zeros(dr.shape[0]), lw]
    cg = np.exp(lw[:, -1] / (dr.shape[1] / 252.0)) - 1; mdd = np.expm1((lw - np.maximum.accumulate(lw, axis=1)).min(axis=1)); return cg, mdd
OUT = {}
for raw in (False, True):
    X = R.W('X', raw=raw); T = X.T; sl = slice(WARM + 1, T)
    rf = np.nan_to_num(X.m['rf'])[:, sl]; u = np.nan_to_num(X.m['r'])[:, sl] + DQ / 252
    qcg, qmd = perf(u); q10 = np.percentile(qmd, 10)
    res = {}
    for sleeve in (['DEF3', 'LTT', 'B10'] if raw else ['DEF3', 'SPX', 'VALUE']):
        S = X.pan[sleeve][0][:, sl] + (DD.SLEEVES.get(sleeve, ('', 0.001))[1] if sleeve in DD.SLEEVES else 0.001) / 252   # gross of expense ratio
        for sp_name, sp in (('fric', 0.0), ('tqqq', 0.01225), ('tqqq_nodiv', 0.01225 + DQ)):
            best = None
            for n, d in itertools.product(np.round(np.arange(0.5, 1.251, 0.05), 3), np.round(np.arange(0.0, 1.01, 0.1), 2)):
                lev = max(n + d - 1, 0.0)
                dr = n * u + d * S + (1 - n - d) * rf - sp * lev / 252
                cg, md = perf(dr); pair = float(np.median(cg - qcg)); ddm = 1 - abs(np.percentile(md, 10)) / abs(q10)
                ok = pair > 0 and np.median(cg) > np.median(qcg) and np.percentile(cg, 10) >= np.percentile(qcg, 10) and ddm >= 0.1
                k = '%s|%s|n%.2f|d%.1f' % (sleeve, sp_name, n, d); res[k] = dict(pair=pair, ddm=float(ddm), med=float(np.median(cg)), gate=bool(ok))
            # frontier: max pair subject to ddm >= 0.10, and max ddm subject to pair > 0
            sub = {k: v for k, v in res.items() if k.startswith(sleeve + '|' + sp_name + '|')}
            a = [(v['pair'], k, v['ddm']) for k, v in sub.items() if v['ddm'] >= 0.10]
            b = [(v['ddm'], k, v['pair']) for k, v in sub.items() if v['pair'] > 0]
            print('raw' if raw else 'neutral', sleeve, sp_name, 'gate passers', sum(v['gate'] for v in sub.values()),
                  '| best pair @ddm>=10%%: %s %+.2fpp (ddm %+.1f%%)' % (max(a)[1], max(a)[0] * 100, max(a)[2] * 100) if a else '',
                  '| best ddm @pair>0: %s %+.1f%% (pair %+.2fpp)' % (max(b)[1], max(b)[0] * 100, max(b)[2] * 100) if b else '', flush=True)
    OUT['raw' if raw else 'neutral'] = dict(qqq=dict(med=float(np.median(qcg)), p10mdd=float(q10)), rows=res)
    del X; DD._P.clear()
L._WORLDS.pop('X', None)
json.dump(OUT, open('/tmp/df5v/limit/exp_static.json', 'w'))
