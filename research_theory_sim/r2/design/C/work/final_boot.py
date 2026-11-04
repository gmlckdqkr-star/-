"""Paired bootstrap (over paths) of the median-CAGR difference rule - hold1x and rule - best constant, fresh ON/OFF worlds."""
import sys, os, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, exec_engine as ee
spec = importlib.util.spec_from_file_location('rule', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rule.py'))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
g = np.random.default_rng(0)
for mech in (True, False):
    w = H.world([10001, 10002, 10003, 10004], 500, mech)
    cr = ee.run(w['r'], w['rf'], R.target_levels(w['close'], w['rf']))['cagr']
    ch = ee.hold(w['r'], w['rf'], 1)['cagr']
    cb = ee.run(w['r'], w['rf'], np.full(w['r'].shape, 0.5))['cagr']
    n = cr.size; d1 = []; d2 = []
    for _ in range(2000):
        i = g.integers(0, n, n); d1.append(np.median(cr[i]) - np.median(ch[i])); d2.append(np.median(cr[i]) - np.median(cb[i]))
    print('mech', mech, 'rule-hold1 %.4f [%.4f, %.4f]  rule-const0.5 %.4f [%.4f, %.4f]  P(rule>hold1 per path) %.3f  hold1 dd80 %.3f' % (
        np.median(cr) - np.median(ch), *np.percentile(d1, [5, 95]), np.median(cr) - np.median(cb), *np.percentile(d2, [5, 95]),
        np.mean(cr > ch), ee.summary(ee.hold(w['r'], w['rf'], 1))['p_dd80']))
