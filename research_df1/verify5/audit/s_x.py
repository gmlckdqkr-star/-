import os, sys, time, json, numpy as np
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5fam as F, dfe, dfk
WN = sys.argv[1]
CF = {c['id']: c for c in F.configs(R.ELIG)}
IDS = ['A3|e1.00|c0.20|GOLD+LTT+DEF3|none', 'A3|e1.00|c0.35|GOLD+LTT+DEF3|none', 'A3|e1.00|c0.20|GOLD+LTT|none',
       'A3|e1.00|c0.20|LTT|none', 'A3|e1.00|c0.20|B10|none', 'A5|DEF3|U0|D2|T200|d0.3', 'A5|DEF3|U0|D1|now|d0.3']
t0 = time.time()
X = R.W(WN); base = {k: X.pan[k] for k in ('TQQQ', 'QLD', 'LTT', 'B10', 'TMF')}
DQn = DD.DQ * (1 - 0.154)
def variant(v):
    for k in base: X.pan[k] = base[k]
    if v in ('div', 'both'):
        X.pan['TQQQ'] = (base['TQQQ'][0] + 3 * DQn / 252, 0.0, 1); X.pan['QLD'] = (base['QLD'][0] + 2 * DQn / 252, 0.0, 1)
    if v in ('tp', 'both'):
        tp = 0.01 / 252
        X.pan['LTT'] = (base['LTT'][0] + tp, base['LTT'][1], 1); X.pan['B10'] = (base['B10'][0] + tp, base['B10'][1], 1); X.pan['TMF'] = (base['TMF'][0] + 3 * tp, 0.0, 1)
hs = [None] if WN == 'REAL' else [30, 10]
res = {}
for vv, over in (('base', {}), ('div', {}), ('tp', {}), ('both', {}), ('notax', dict(tax=0.0))):
    if vv == 'notax': variant('base')
    else: variant(vv)
    Q = {}
    for h in hs:
        hh = None if h in (None, 30) else h; key = WN + ('' if h is None else str(h))
        qcg, qmd, _ = R.qqq(X, hh, **over); Q[key] = (qcg, qmd)
        res.setdefault('QQQ', {})[(vv, key)] = (float(np.median(qcg)), float(np.percentile(qmd, 10)))
    for i in IDS:
        jb = R.job(CF[i], X)
        for h in hs:
            hh = None if h in (None, 30) else h; key = WN + ('' if h is None else str(h))
            cg, md, _ = R.run_job(jb, X, hh, **over); qcg, qmd = Q[key]
            pair = np.median(cg - qcg); med = np.median(cg) - np.median(qcg); p10 = np.percentile(cg, 10) - np.percentile(qcg, 10)
            ddm = 1 - abs(np.percentile(md, 10)) / abs(np.percentile(qmd, 10))
            res.setdefault(i, {})[(vv, key)] = (pair * 100, med * 100, p10 * 100, ddm * 100)
        del jb
    print(vv, 'done %.0fs' % (time.time() - t0), flush=True)
for i, d in res.items():
    print(i)
    for (vv, key), x in d.items():
        if i == 'QQQ': print('   %-6s %-5s med %.4f p10mdd %.4f' % (vv, key, *x))
        else: print('   %-6s %-5s pair %+.3f med %+.3f p10 %+.3f ddm %+.2f' % (vv, key, *x))
