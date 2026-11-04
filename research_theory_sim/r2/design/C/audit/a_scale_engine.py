"""AUDIT (lane C): engine-level scale invariance: rule on close and on close*1000 / *0.001 gives the same traded result."""
import sys, os, importlib.util
TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOP); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import numpy as np, sim, exec_engine as ee
spec = importlib.util.spec_from_file_location('rule', os.path.join(TOP, 'rule.py')); R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
T = 300 + 30 * 252
for mech in (True, False):
    d = sim.simulate(500, T, 10001, mechanism=mech); r, rf = d['r'], d['rf']
    close = 100.0 * np.cumprod(1 + r, axis=1)
    c0 = ee.run(r, rf, R.target_levels(close, rf))['cagr']
    for k in (1000.0, 0.001):
        ck = ee.run(r, rf, R.target_levels(close * k, rf))['cagr']
        print('mech %s scale %g: traded CAGR bit-identical on all %d paths: %s (max |diff| %.3g)' % (
            mech, k, c0.size, np.array_equal(c0, ck), np.abs(c0 - ck).max()))
