"""AUDIT (lane D, TS2 r2): rule.py interface, input immutability, NaN / zero / flat stretches, scale invariance, speed."""
import sys, time, ast, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import rule, sim

src = open('/mnt/project-files/research/theory_sim/r2/design/D/rule.py').read()
tree = ast.parse(src)
imps = set()
for nd in ast.walk(tree):
    if isinstance(nd, ast.Import): imps |= {a.name.split('.')[0] for a in nd.names}
    if isinstance(nd, ast.ImportFrom): imps.add((nd.module or '').split('.')[0])
print('imports:', sorted(imps), 'OK' if imps <= {'numpy', 'math'} else 'FAIL')
bad = [w for w in ('open(', 'load', 'save', 'os.', 'sys.', 'eval(', 'exec(', '__import__', 'random', 'time') if w in src]
print('suspicious tokens in source:', bad)
print('INPUTS', rule.INPUTS, 'PARAMS', rule.PARAMS)
import inspect
print('signature', inspect.signature(rule.target_levels))
pv = [nd for nd in tree.body if isinstance(nd, ast.Assign) and any(getattr(t, 'id', '') == 'PARAMS' for t in nd.targets)]
print('PARAMS is a literal:', all(isinstance(nd.value, ast.Dict) and all(isinstance(v, ast.Constant) for v in nd.value.values) for nd in pv))

T = 7860
d = sim.simulate(60, T, 777, mechanism=True)
r, rf, y = d['r'], d['rf'], d['y10']
close = 1000.0 * np.cumprod(1 + r, axis=1)
# edge cases: NaN before the market opens, zeros, flat stretches, NaN gaps, NaN rf, NaN y10
c = close.copy(); f = rf.copy(); yy = y.copy()
c[0, :500] = np.nan                    # market not open for 500 columns
c[1, :200] = 0.0                       # zeros before opening
c[2, 1000:1300] = c[2, 999]            # flat stretch 300 days
c[3, 2000:2010] = np.nan               # NaN gap mid-path
c[4, 4000] = 0.0                       # single zero mid-path
c[5, :] = 5.0                          # entirely flat path
c[6, :] = np.nan                       # entirely NaN path
f[7, 100:400] = np.nan                 # NaN rf
yy[8, :] = np.nan
c[9, 3000:3050] = np.inf               # inf in close
c[10, 5000:5020] = -c[10, 5000:5020]   # negative prices
inputs = [c.copy(), f.copy(), yy.copy()]
t0 = time.time()
B = rule.target_levels(c, f, yy)
print('edge-case run %.2fs' % (time.time() - t0))
print('inputs unchanged:', all(np.array_equal(a, b, equal_nan=True) for a, b in zip(inputs, (c, f, yy))))
print('output shape', B.shape, B.dtype, 'finite-or-NaN in [0,3]:', bool(np.all(np.isnan(B) | ((B >= 0) & (B <= 3)))),
      'on 0.5 grid:', bool(np.all(np.isnan(B) | (np.abs(B * 2 - np.round(B * 2)) < 1e-12))), 'NaN count', int(np.isnan(B).sum()))
print('path0 (NaN 500): level at 499/520/600:', B[0, 499], B[0, 520], B[0, 600])
print('path2 flat 1000-1300: levels at 999/1030/1299/1350:', B[2, 999], B[2, 1030], B[2, 1299], B[2, 1350])
print('path5 all flat: unique', np.unique(B[5])); print('path6 all NaN: unique', np.unique(B[6]))
for k in (0, 1, 2, 3, 4, 7, 8, 9, 10):
    print('  path', k, 'unique levels', np.unique(B[k]))
# also run with y10=None, default params, 1 path and T short
B2 = rule.target_levels(close, rf); B3 = rule.target_levels(close, rf, None, rule.PARAMS)
print('y10 ignored (y vs None identical):', np.array_equal(B2, rule.target_levels(close, rf, y)), np.array_equal(B2, B3))
Bs = rule.target_levels(close[:1, :400], rf[:1, :400]); print('short T=400 P=1 ok', Bs.shape)
# scale invariance
B0 = rule.target_levels(close, rf, y)
for sc in (1000.0, 1e-3, 7.77, 1e6, 0.0123):
    print('scale x%g identical:' % sc, np.array_equal(B0, rule.target_levels(close * sc, rf, y), equal_nan=True))
# alternative normalisation: close starting at 1 instead of 1000
print('start at 1 identical:', np.array_equal(B0, rule.target_levels(np.cumprod(1 + r, axis=1), rf, y)))
# float32 / int inputs
print('float32 input runs:', rule.target_levels(close.astype(np.float32), rf.astype(np.float32)).dtype)
# speed P=500, T=10000
d = sim.simulate(500, 10000, 778, mechanism=True)
cl = np.cumprod(1 + d['r'], axis=1)
t0 = time.time(); Bp = rule.target_levels(cl, d['rf'], d['y10']); dt = time.time() - t0
print('speed P=500 T=10000: %.2fs' % dt, 'OK' if dt < 60 else 'FAIL', Bp.shape, Bp.dtype)
# determinism
print('deterministic:', np.array_equal(Bp, rule.target_levels(cl, d['rf'], d['y10'])))
