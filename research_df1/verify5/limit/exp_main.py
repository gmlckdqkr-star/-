"""E1/E2/E3 (+tax0, ALL) on X30 for the frontier set. Post-hoc, report-only. Writes /tmp/df5v/limit/exp_main.json"""
import os, sys, time, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5run as R, df5stress as ST, df5lib as L, df5data as DD
t0 = time.time()
def log(*a): print('%6.0fs' % (time.time() - t0), *a, flush=True)
CFGS = ['A3|e1.00|c0.20|GOLD+LTT+DEF3|none', 'A3|e1.00|c0.20|DEF3|none', 'A3|e1.00|c0.35|DEF3|none', 'A3|e1.00|c0.50|DEF3|none',
        'A3|e1.00|c0.20|SPX|none', 'A3|e1.25|c0.50|DEF3|none', 'A3|e1.00|c0.20|B10|none', 'A3|e1.00|c0.20|LTT|none',
        'A5|DEF3|U0|D1|now|d0.3', 'A5|DEF3|U0|D2|T200|d0.3', 'A5|DEF3|U0|D0|-|d0.3',
        'A9|MIX|N|L1.5', 'A7|HAL151', 'A1|N|V0.30w20L1.5|DEF3', 'A1|N|V0.20w60L1.5|DEF3', 'A6|N10|none']
DQ = DD.DQ; DY = DD.DY
idx = ST.cfg_index()
OUT = {}
def stat(cg, md, qcg, qmd):
    d = R.summ(cg, md, qcg); d['ddm'] = 1 - abs(d['mdd_p10']) / abs(float(np.percentile(qmd, 10)))
    d['gate'] = bool(d['pair'] > 0 and d['cagr'] > np.median(qcg) and d['p10'] >= np.percentile(qcg, 10) - 1e-12 and d['ddm'] >= 0.1 - 1e-12)
    d['both0'] = bool(d['pair'] > 0 and d['ddm'] >= 0)
    return d

def patch_div(X, spx_too=False):
    saved = {}
    adds = {'QLD': 2 * DQ / 252, 'TQQQ': 3 * DQ / 252}
    if spx_too: adds.update({'SSO': 2 * DY / 252, 'UPRO': 3 * DY / 252})
    for k, a in adds.items():
        saved[k] = X.pan[k]; r, inc, hv = X.pan[k]; X.pan[k] = (r + a, inc, hv)
    return saved
def unpatch(X, saved):
    for k, v in saved.items(): X.pan[k] = v

def run_cond(X, tag, over, div=False, spx_too=False, only=None):
    saved = patch_div(X, spx_too) if div else {}
    qcg, qmd, _ = R.qqq(X, None, **over)
    OUT.setdefault('QQQ', {})[tag] = R.summ(qcg, qmd)
    for cid in (only or CFGS):
        cfg = idx[cid]; ov = dict(over)
        if div and cfg['fam'] in ('A1', 'A2', 'A7', 'A8'): ov['er3'] = 0.0245 - 3 * DQ     # dfe TQQQ leg
        cg, md, _ = ST.runner(cfg, X, None, **ov)
        OUT.setdefault(cid, {})[tag] = stat(cg, md, qcg, qmd)
    unpatch(X, saved)
    log(tag, 'QQQ med %.4f p10mdd %.4f' % (np.median(qcg), np.percentile(qmd, 10)),
        'gate', sum(OUT[c][tag]['gate'] for c in (only or CFGS)), 'both0', sum(OUT[c][tag]['both0'] for c in (only or CFGS)))

X = R.W('X'); log('X loaded')
FR = dict(cost=0.0, delay=1, tax=0.0)
run_cond(X, 'base', {})
run_cond(X, 'E1div', {}, div=True)
run_cond(X, 'E1div_spx', {}, div=True, spx_too=True, only=['A9|MIX|N|L1.5'])
run_cond(X, 'E2cost0', dict(cost=0.0))
run_cond(X, 'E2cost0_d1', dict(cost=0.0, delay=1))
run_cond(X, 'E2c_tax0', FR)
run_cond(X, 'ALL_neutral', FR, div=True, spx_too=True)
json.dump(OUT, open('/tmp/df5v/limit/exp_main.json', 'w'))
del X; DD._P.clear(); L._WORLDS.pop('X', None)
X = R.W('X', raw=True); log('X raw loaded'); OUT['shift_raw'] = {k: v * 252 for k, v in X.pan['meta']['shift'].items()}
run_cond(X, 'E3raw', {})
run_cond(X, 'ALL_raw', FR, div=True, spx_too=True)
json.dump(OUT, open('/tmp/df5v/limit/exp_main.json', 'w'))
del X; DD._P.clear(); L._WORLDS.pop('X', None)
log('done')
