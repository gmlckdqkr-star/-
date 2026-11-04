"""AUDIT (lane D, TS2 r2): independent re-run of G-ON / G-OFF and the fresh-seed headline with exec_engine.
usage: python gates.py SEED P [rob]"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import exec_engine as ee, sim, rule

T = 7860
seed = int(sys.argv[1]); P = int(sys.argv[2]); rob = len(sys.argv) > 3 and sys.argv[3] == 'rob'
out = {}
for mech in (True, False):
    t0 = time.time()
    d = sim.simulate(P, T, seed, mechanism=mech)
    r, rf, y = d['r'], d['rf'], d['y10']
    assert np.isfinite(r).all() and np.isfinite(rf).all() and np.isfinite(y).all()
    close = 1000.0 * np.cumprod(1 + r, axis=1)
    B = rule.target_levels(close, rf, y)
    s = ee.summary(ee.run(r, rf, B))
    row = dict(rule=s['cagr_med'], rule_p10=s['cagr_p10'], rule_p_dd80=s['p_dd80'], rule_avg_level=s['avg_level_med'],
               rule_trades=s['trades_per_year_med'])
    for lev in (1, 2, 3):
        row['hold%d' % lev] = ee.summary(ee.hold(r, rf, lev))['cagr_med']
    cm = {}
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        cm[L] = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']
    row['const'] = {str(k): v for k, v in cm.items()}
    bl = max(cm, key=cm.get); row['best_const_level'] = bl; row['best_const'] = cm[bl]
    if rob:
        row['delay3'] = ee.summary(ee.run(r, rf, B, delay=3))['cagr_med']
        row['delay5'] = ee.summary(ee.run(r, rf, B, delay=5))['cagr_med']
        row['cost2x'] = ee.summary(ee.run(r, rf, B, cost=0.006))['cagr_med']
    if mech:
        row['G_ON_pass'] = bool(row['rule'] > row['hold1'] and row['rule'] > row['best_const'])
    else:
        row['G_OFF_loss_pp'] = 100 * (row['best_const'] - row['rule'])
        row['G_OFF_pass'] = bool(row['best_const'] - row['rule'] <= 0.010)
    row['secs'] = round(time.time() - t0, 1)
    out['ON' if mech else 'OFF'] = row
    print(seed, P, 'ON' if mech else 'OFF', json.dumps(row), flush=True)
