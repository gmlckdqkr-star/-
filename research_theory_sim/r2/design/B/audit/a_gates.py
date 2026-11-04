import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule
T = 7860
seed = int(sys.argv[1]); P = int(sys.argv[2]); extra = len(sys.argv) > 3 and sys.argv[3] == 'extra'
out = {}
for mech in (True, False):
    t0 = time.time()
    s = sim.simulate(P, T, seed, mech); r, rf = s['r'], s['rf']
    close = 100.0 * np.exp(np.cumsum(np.log1p(r), axis=1))
    B = rule.target_levels(close, rf)
    d = {}
    sm = ee.summary(ee.run(r, rf, B))
    d['rule'] = sm['cagr_med']; d['rule_p10'] = sm['cagr_p10']; d['rule_pdd80'] = sm['p_dd80']; d['rule_avg_level'] = sm['avg_level_med']; d['tpy'] = sm['trades_per_year_med']
    for lev in (1, 2, 3): d['hold%d' % lev] = ee.summary(ee.hold(r, rf, lev))['cagr_med']
    best, bl = -9, None
    for L in np.arange(0.5, 3.01, 0.5):
        c = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']; d['const%.1f' % L] = c
        if c > best: best, bl = c, float(L)
    d['best_const'] = best; d['best_const_level'] = bl
    if extra:
        d['delay3'] = ee.summary(ee.run(r, rf, B, delay=3))['cagr_med']
        d['delay5'] = ee.summary(ee.run(r, rf, B, delay=5))['cagr_med']
        d['cost2x'] = ee.summary(ee.run(r, rf, B, cost=0.006))['cagr_med']
    if mech:
        d['G_ON_pass'] = bool(d['rule'] > d['hold1'] and d['rule'] > d['best_const'])
    else:
        d['G_OFF_pass'] = bool(d['rule'] >= d['best_const'] - 0.01)
    d['secs'] = round(time.time() - t0, 1)
    out['ON' if mech else 'OFF'] = d
    print(seed, P, 'ON ' if mech else 'OFF', json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in d.items()}), flush=True)
