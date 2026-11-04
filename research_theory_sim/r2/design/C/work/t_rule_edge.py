"""Edge-case tests for rule.py: scale invariance, NaN/zero/flat stretches, causality, input not modified, shape, range."""
import sys, os, importlib.util
TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('rule', os.path.join(TOP, 'rule.py')); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
import numpy as np
g = np.random.default_rng(5)
P, T = 20, 3000
r = g.normal(0.0003, 0.011, (P, T)); r[:, 0] = 0
close = 100 * np.cumprod(1 + r, axis=1)
c2 = close.copy()
c2[0, :500] = np.nan                     # market not open yet
c2[1, 1000:1100] = c2[1, 999]            # flat stretch
c2[2, 200:205] = 0.0                     # zeros
c2[3, 1500] = np.nan                     # single gap
keep = c2.copy()
L = R.target_levels(c2, np.zeros_like(c2))
assert np.array_equal(np.isnan(keep), np.isnan(c2)) and np.allclose(np.nan_to_num(keep), np.nan_to_num(c2)), 'input modified'
assert L.shape == (P, T) and L.dtype == np.float64
assert np.all((np.isnan(L)) | ((L >= 0) & (L <= 3)))
L2 = R.target_levels(c2 * 1234.5, np.zeros_like(c2))
assert np.allclose(np.nan_to_num(L, nan=-1), np.nan_to_num(L2, nan=-1), atol=1e-9), 'not scale invariant'
# causality: changing the future does not change the past
c3 = c2.copy(); c3[:, 2000:] *= np.exp(g.normal(0, 0.05, (P, T - 2000)).cumsum(axis=1))
L3 = R.target_levels(c3, np.zeros_like(c3))
assert np.allclose(np.nan_to_num(L[:, :2000], nan=-1), np.nan_to_num(L3[:, :2000], nan=-1)), 'not causal'
print('first valid column row0 (NaN until 500 + 250 obs):', np.argmax(np.isfinite(L[0])))
print('levels pct', np.nanpercentile(L, [5, 50, 95]).round(2), 'NaN share', np.isnan(L).mean().round(3))
print('ALL EDGE TESTS PASSED')
