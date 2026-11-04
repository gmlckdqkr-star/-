"""AUDIT (blind auditor, lane C): re-run G-ON / G-OFF and the fresh-seed headline on seeds 10001-10004 (P=500 each,
2000 paths per world), exactly as design_log.md / work/final_eval.py build them, but with independent code (no harness
import, so nothing is appended to work/variants.csv). Synthetic data only."""
import sys, os, json, time, importlib.util
TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOP); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import numpy as np, sim, exec_engine as ee
spec = importlib.util.spec_from_file_location('rule', os.path.join(TOP, 'rule.py')); R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
T = 300 + 30 * 252
SEEDS = [int(s) for s in (sys.argv[2].split(',') if len(sys.argv) > 2 else ['10001', '10002', '10003', '10004'])]
mech = sys.argv[1] == 'ON'
t0 = time.time()
rs, fs = [], []
for sd in SEEDS:
    d = sim.simulate(500, T, sd, mechanism=mech); rs.append(d['r']); fs.append(d['rf'])
r = np.concatenate(rs); rf = np.concatenate(fs); del rs, fs, d
close = 100.0 * np.cumprod(1 + r, axis=1)
print('sim %.0fs P=%d finite r %s rf %s' % (time.time() - t0, r.shape[0], np.isfinite(r).all(), np.isfinite(rf).all()), flush=True)
B = R.target_levels(close, rf)
out = dict(world=sys.argv[1], seeds=SEEDS, n_paths=int(r.shape[0]))
s = ee.summary(ee.run(r, rf, B)); out['rule'] = s
out['hold'] = {L: ee.summary(ee.hold(r, rf, L))['cagr_med'] for L in (1, 2, 3)}
out['const'] = {}
for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
    out['const'][L] = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']
bl = max(out['const'], key=lambda k: out['const'][k]); out['best_const_level'] = bl; out['best_const'] = out['const'][bl]
out['delay3'] = ee.summary(ee.run(r, rf, B, delay=3))['cagr_med']
out['delay5'] = ee.summary(ee.run(r, rf, B, delay=5))['cagr_med']
out['cost2x'] = ee.summary(ee.run(r, rf, B, cost=0.006))['cagr_med']
rm = s['cagr_med']
out['vs_hold1_pp'] = 100 * (rm - out['hold'][1]); out['vs_best_pp'] = 100 * (rm - out['best_const'])
out['G_ON_pass'] = bool(rm > out['hold'][1] and rm > out['best_const']) if mech else None
out['G_OFF_pass'] = bool(rm >= out['best_const'] - 0.01) if not mech else None
out['time_s'] = time.time() - t0
print(json.dumps(out, default=float, indent=1), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gates_%s_%s.json' % (sys.argv[1], SEEDS[0])), 'w'), default=float, indent=1)
