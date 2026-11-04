import sys, time, ast, inspect, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule
src = open('/mnt/project-files/research/theory_sim/r2/design/B/rule.py').read()
tree = ast.parse(src)
imps = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
print('imports:', [(type(n).__name__, [a.name for a in n.names], getattr(n, 'module', None)) for n in imps])
names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
print('suspicious names:', sorted(names & {'open', 'eval', 'exec', '__import__', 'compile', 'globals', 'getattr', 'input'}))
print('INPUTS', rule.INPUTS, 'PARAMS', rule.PARAMS, 'sig', inspect.signature(rule.target_levels))
print('docstring lines', len([l for l in (rule.__doc__ or '').strip().splitlines()]))
print('PARAMS is literal dict:', isinstance([n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == 'PARAMS'][0].value, ast.Dict))
T = 7860
s = sim.simulate(200, T, 31, True)
r, rf, y10 = s['r'], s['rf'], s['y10']
close = 100.0 * np.exp(np.cumsum(np.log1p(r), axis=1))
c0, f0, y0 = close.copy(), rf.copy(), y10.copy()
L = rule.target_levels(close, rf, y10)
print('inputs unmodified:', np.array_equal(c0, close), np.array_equal(f0, rf), np.array_equal(y0, y10))
print('out shape/dtype', L.shape, L.dtype, 'finite in [0,3]:', bool(np.all((L[np.isfinite(L)] >= 0) & (L[np.isfinite(L)] <= 3))), 'any inf', bool(np.isinf(L).any()),
      'NaN cols at start', int(np.isnan(L).all(0).sum()), 'NaN after 300:', int(np.isnan(L[:, 300:]).sum()))
L2 = rule.target_levels(close, rf)  # y10 omitted
print('y10 ignored:', np.array_equal(L, L2, equal_nan=True))
L3 = rule.target_levels(close, rf, None, rule.PARAMS)
print('params positional ok:', np.array_equal(L, L3, equal_nan=True))
# scale invariance
for k in (1000.0, 1e-3, 1024.0, 7.3):
    Lk = rule.target_levels(close * k, rf)
    eq = np.array_equal(L2, Lk, equal_nan=True)
    md = np.nanmax(np.abs(L2 - Lk))
    print('scale x%g: bit-identical %s, max abs diff %.3g, NaN pattern same %s' % (k, eq, md, np.array_equal(np.isnan(L2), np.isnan(Lk))))
# effect after engine
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
Lk = rule.target_levels(close * 1000.0, rf)
a = ee.run(r, rf, L2)['cagr']; b = ee.run(r, rf, Lk)['cagr']
print('engine CAGR identical under x1000:', np.array_equal(a, b), 'max diff', np.max(np.abs(a - b)))
# NaN / zero / flat / garbage handling
c3 = close[:8].copy(); r3 = rf[:8].copy()
c3[0, :800] = np.nan                    # market not open yet
c3[1, :500] = 0.0                       # zeros before open
c3[2, 1000:1600] = c3[2, 1000]          # flat stretch
c3[3, 2000:2010] = np.nan               # holiday gap
c3[4, 3000:3005] = 0.0                  # zeros in the middle
c3[5, :] = 5.0                          # entirely flat
c3[6, :] = np.nan                       # entirely NaN
c3[7, 4000] = np.inf; c3[7, 4001] = -3.0  # garbage values
r3[0, :100] = np.nan; r3[3, 2000:2100] = np.nan
with np.errstate(all='raise'):
    try:
        L5 = rule.target_levels(c3, r3); print('no FP warnings raised')
    except FloatingPointError as e:
        print('FP error under errstate raise:', e); 
        with np.errstate(all='ignore'): L5 = rule.target_levels(c3, r3)
fin = L5[np.isfinite(L5)]
print('nan-handling: finite in [0,3]:', bool(np.all((fin >= 0) & (fin <= 3))), 'inf:', bool(np.isinf(L5).any()))
print('first valid output col per path', [int(np.argmax(np.isfinite(L5[i]))) if np.isfinite(L5[i]).any() else -1 for i in range(8)])
print('flat path 2 levels at 999/1300/1599/1601:', L5[2, [999, 1300, 1599, 1601]])
print('all-flat path 5 all NaN:', bool(np.isnan(L5[5]).all()), ' all-NaN path 6 all NaN:', bool(np.isnan(L5[6]).all()))
print('path 7 around garbage', L5[7, 3998:4004], 'finite after:', bool(np.isfinite(L5[7, 4001:]).all()))
print('path 4 around zeros', L5[4, 2998:3007])
# int input / 1-D
print('1-D input shape', rule.target_levels(close[0], rf[0]).shape)
# speed
g = np.random.default_rng(1); cc = 100 * np.exp(np.cumsum(g.normal(0.0003, 0.011, (500, 10000)), axis=1)); ff = np.full((500, 10000), 0.03 / 252)
t0 = time.time(); Lsp = rule.target_levels(cc, ff); print('speed P=500 T=10000: %.2fs, shape %s' % (time.time() - t0, Lsp.shape))
# determinism
print('deterministic:', np.array_equal(rule.target_levels(close, rf), L2, equal_nan=True))
