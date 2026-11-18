"""Same off-grid static TQQQ/QQQ/DEF3 mixes, engine with full conventions, but raw (un-neutralized) DEF3. X30 (and X10 for the best). Post-hoc."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5run as R, df5lib as L, df5data as DD
OUT = {}
X = R.W('X', raw=True)
for h, key, pairs in ((None, 'X30', [(0.60, 0.80), (0.65, 0.70), (0.70, 0.60), (0.55, 0.80)]), (10, 'X10', [(0.60, 0.80)])):
    qcg, qmd, _ = R.qqq(X, h); q10 = np.percentile(qmd, 10)
    for e, c in pairs:
        cfg = dict(fam='A3', e=e, c=c, dmix=['DEF3'], gate='none'); a = (e - 1 + c) / 2; b = 1 - c - a
        cg, md, _ = R.run_job(R.job(cfg, X), X, h)
        d = R.summ(cg, md, qcg); d['ddm'] = 1 - abs(d['mdd_p10']) / abs(q10)
        d['gate'] = bool(d['pair'] > 0 and d['cagr'] > np.median(qcg) and d['p10'] >= np.percentile(qcg, 10) - 1e-12 and d['ddm'] >= 0.1 - 1e-12)
        nm = 'A3x|e%.2f|c%.2f|DEF3raw (TQQQ %.3f QQQ %.3f)' % (e, c, a, b); OUT.setdefault(nm, {})[key] = d
        print('%-46s %s med %.2f%% (QQQ %.2f%%) pair %+.2fpp p10 %.2f%% (QQQ %.2f%%) p10MDD %.1f%% ddm %+.1f%% %s' % (nm, key, d['cagr'] * 100, np.median(qcg) * 100, d['pair'] * 100,
              d['p10'] * 100, np.percentile(qcg, 10) * 100, d['mdd_p10'] * 100, d['ddm'] * 100, 'GATE' if d['gate'] else ''), flush=True)
json.dump(OUT, open('/tmp/df5v/limit/exp_static_engine_raw.json', 'w'))
del X; DD._P.clear(); L._WORLDS.pop('X', None)
