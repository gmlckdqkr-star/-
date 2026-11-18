"""Off-grid A3-style static mixes (TQQQ/QQQ/DEF3, 63-day rebalance) through the DF5 engine with full conventions, X30 and X10. Post-hoc."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5run as R, df5lib as L, df5data as DD
PAIRS = [(0.60, 0.80), (0.65, 0.70), (0.70, 0.60), (0.55, 0.80), (0.60, 0.70), (0.65, 0.60), (0.50, 0.80), (0.70, 0.50), (0.75, 0.40), (0.80, 0.30)]
OUT = {}
X = R.W('X')
for h, key in ((None, 'X30'), (10, 'X10')):
    qcg, qmd, _ = R.qqq(X, h); q10 = np.percentile(qmd, 10)
    OUT.setdefault('QQQ', {})[key] = R.summ(qcg, qmd)
    for e, c in PAIRS:
        cfg = dict(fam='A3', e=e, c=c, dmix=['DEF3'], gate='none')
        a = (e - 1 + c) / 2; b = 1 - c - a; assert b >= -1e-12
        cg, md, _ = R.run_job(R.job(cfg, X), X, h)
        d = R.summ(cg, md, qcg); d['ddm'] = 1 - abs(d['mdd_p10']) / abs(q10)
        d['gate'] = bool(d['pair'] > 0 and d['cagr'] > np.median(qcg) and d['p10'] >= np.percentile(qcg, 10) - 1e-12 and d['ddm'] >= 0.1 - 1e-12)
        nm = 'A3x|e%.2f|c%.2f|DEF3|none (TQQQ %.3f QQQ %.3f)' % (e, c, a, b); OUT.setdefault(nm, {})[key] = d
        print('%-48s %s med %.2f%% pair %+.2fpp p10 %.2f%% (QQQ %.2f%%) p10MDD %.1f%% ddm %+.1f%% %s' % (nm, key, d['cagr'] * 100, d['pair'] * 100, d['p10'] * 100,
              np.percentile(qcg, 10) * 100, d['mdd_p10'] * 100, d['ddm'] * 100, 'GATE' if d['gate'] else ''), flush=True)
json.dump(OUT, open('/tmp/df5v/limit/exp_static_engine.json', 'w'))
del X; DD._P.clear(); L._WORLDS.pop('X', None)
