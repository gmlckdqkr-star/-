"""selection harness: seeds 11 and 12 (within 1-999), mechanism ON and OFF. Every evaluation is logged with a running N."""
import sys, os, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import sim, exec_engine as ee
np.seterr(all='ignore')
T = 7860
LOG = '/mnt/project-files/research/theory_sim/design/L1/work/variants.csv'
_cache = {}

def data(seed, mech, P=1500, prior_scale=1.0):
    k = (seed, mech, P, prior_scale)
    if k not in _cache:
        s = sim.simulate(P, T, seed=seed, mechanism=mech, prior_scale=prior_scale)
        _cache[k] = (s['r'], s['rf'])
    return _cache[k]

def next_n():
    if not os.path.exists(LOG): return 1
    with open(LOG) as f: return sum(1 for _ in f)

def log(tag, params, res):
    n = next_n()
    new = not os.path.exists(LOG)
    with open(LOG, 'a') as f:
        if new: f.write('N,tag,params,J,on_med,off_med,on_p10,on_tpy\n'); n = 1
        f.write(f'{n},{tag},"{json.dumps(params)}",{res["J"]:.5f},{res["on"]:.5f},{res["off"]:.5f},{res["on_p10"]:.5f},{res["on_tpy"]:.2f}\n')
    return n

def evaluate(fn, params, tag, seed=11, P=1500, do_log=True, **kw):
    out = {}
    for mech in (True, False):
        r, rf = data(seed, mech, P)
        B = fn(np.cumprod(1 + r, axis=1), rf, params)
        sm = ee.summary(ee.run(r, rf, B, **kw))
        out['on' if mech else 'off'] = sm['cagr_med']
        if mech: out['on_p10'] = sm['cagr_p10']; out['on_tpy'] = sm['trades_per_year_med']; out['on_lev'] = sm['avg_level_med']
    out['J'] = 0.5 * out['on'] + 0.5 * out['off']
    if do_log: out['N'] = log(tag + f'@s{seed}', params, out)
    return out
