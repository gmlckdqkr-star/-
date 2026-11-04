"""design helpers (selection only). Variant counter appends to work/variants.jsonl."""
import sys, json, time, os, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim
HERE = os.path.dirname(os.path.abspath(__file__))
T = 7860
_cache = {}
def world(P, seed, mech):
    k = (P, seed, mech)
    if k not in _cache:
        s = sim.simulate(P, T, seed, mech)
        close = np.exp(np.cumsum(np.log1p(s['r']), axis=1)) * 100.0
        _cache[k] = (s, close)
    return _cache[k]
def ewm(a, h, init=None):
    lam = 1 - 0.5 ** (1 / h); out = np.empty_like(a)
    s = a[:, 0].copy() if init is None else init.copy()
    for t in range(a.shape[1]):
        s = s + lam * (a[:, t] - s); out[:, t] = s
    return out
def score(B, s, delay=2, cost=0.003):
    res = ee.run(s['r'], s['rf'], B, delay=delay, cost=cost)
    return ee.summary(res)
def baselines(s):
    r, rf = s['r'], s['rf']; out = {}
    for lev in (1, 2, 3): out['hold%d' % lev] = ee.summary(ee.hold(r, rf, lev))['cagr_med']
    best = -9; bl = None
    for L in np.arange(0.5, 3.01, 0.5):
        c = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']; out['const%.1f' % L] = c
        if c > best: best, bl = c, L
    out['best_const'] = best; out['best_const_level'] = bl
    return out
def log_variant(name, params, seeds, P, results):
    fn = os.path.join(HERE, 'variants.jsonl')
    n = 0
    if os.path.exists(fn):
        with open(fn) as f: n = sum(1 for _ in f)
    rec = dict(N=n + 1, time=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), name=name, params=params, seeds=seeds, P=P, results=results)
    with open(fn, 'a') as f: f.write(json.dumps(rec) + '\n')
    return n + 1
