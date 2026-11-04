"""evaluation harness for rule design (selection seeds 1-999 only; fresh seeds >= 10000 only for final numbers)."""
import sys, time, json, os
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np
import exec_engine as ee
import sim

T = 300 + 30 * 252
_cache = {}
COUNT_FILE = '/mnt/project-files/research/theory_sim/r2/design/A/work/variant_count.json'


def world(seed, P, mech, **kw):
    key = (seed, P, mech, tuple(sorted(kw.items())))
    if key not in _cache:
        _cache[key] = sim.simulate(P, T, seed, mechanism=mech, **kw)
    return _cache[key]


def close_of(r):
    return np.cumprod(1 + r, axis=1)


def evaluate(B, w, delay=2, cost=0.003):
    res = ee.run(w['r'], w['rf'], B, delay=delay, cost=cost)
    return ee.summary(res)


def baselines(w):
    out = {}
    for lev in (1, 2, 3):
        out['hold%d' % lev] = ee.summary(ee.hold(w['r'], w['rf'], lev))['cagr_med']
    P, TT = w['r'].shape
    cl = {}
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        cl[L] = ee.summary(ee.run(w['r'], w['rf'], np.full((P, TT), L)))['cagr_med']
    out['const'] = cl
    bL = max(cl, key=cl.get)
    out['best_const_level'] = bL; out['best_const'] = cl[bL]
    return out


def bump(n=1, tag=''):
    try:
        d = json.load(open(COUNT_FILE))
    except Exception:
        d = dict(N=0, log=[])
    d['N'] += n; d['log'].append([tag, n])
    json.dump(d, open(COUNT_FILE, 'w'))
    return d['N']
