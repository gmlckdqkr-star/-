"""AUDIT (lane C): interface, edge cases, scale invariance, speed and exact causality of rule.py. Synthetic data only."""
import sys, os, ast, inspect, time, importlib.util
TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOP)
import numpy as np, sim
src = open(os.path.join(TOP, 'rule.py')).read()
imps = set()
for nd in ast.walk(ast.parse(src)):
    if isinstance(nd, ast.Import): imps |= {a.name for a in nd.names}
    if isinstance(nd, ast.ImportFrom): imps.add(nd.module)
print('imports:', sorted(imps), 'OK' if imps <= {'numpy', 'math'} else 'BAD')
bad_tokens = [t for t in ('open(', 'eval(', 'exec(', '__import__', 'os.', 'sys.', 'np.load', 'np.save', 'random') if t in src]
print('suspicious tokens in rule.py:', bad_tokens)
spec = importlib.util.spec_from_file_location('rule', os.path.join(TOP, 'rule.py')); R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
print('INPUTS', R.INPUTS, '| PARAMS', R.PARAMS, '| signature', inspect.signature(R.target_levels))
assert R.INPUTS in (('close', 'rf'), ('close', 'rf', 'y10'))
sg = inspect.signature(R.target_levels); assert list(sg.parameters) == ['close', 'rf', 'y10', 'params']
assert sg.parameters['y10'].default is None and sg.parameters['params'].default is R.PARAMS

T = 7860
d = sim.simulate(250, T, 4242, mechanism=True)        # auditor's own seed, not used by the designer
r = d['r'][:60]; rf = d['rf'][:60]; y10 = d['y10'][:60]
close = 100.0 * np.cumprod(1 + r, axis=1)
P = close.shape[0]
# edge cases in the past
c = close.copy()
c[0, :800] = np.nan                    # market not open yet
c[1, 1000:1200] = c[1, 999]            # flat stretch
c[2, 200:260] = 0.0                    # zeros
c[3, 1500] = np.nan; c[3, 3000:3003] = np.nan   # gaps
c[4, :] = np.nan                       # never opens
c[5, 2000] = np.inf; c[5, 2001] = -5.0 # garbage values
c[6, :] = 37.0                         # perfectly flat path
c[7, 4000:] = 0.0                      # goes to zero and stays
keep = [c.copy(), rf.copy(), y10.copy()]
for a in (c, rf, y10): a.setflags(write=False)       # read-only inputs: must not be written
t0 = time.time()
L = R.target_levels(c, rf, y10)
print('call time P=%d T=%d: %.2fs' % (P, T, time.time() - t0))
same = lambda a, b: a.shape == b.shape and np.array_equal(a.view(np.int64), b.view(np.int64))
print('inputs unchanged (bitwise):', all(same(a, b) for a, b in zip((c, rf, y10), keep)))
print('shape', L.shape, 'dtype', L.dtype, 'range ok', bool(np.all(np.isnan(L) | ((L >= 0) & (L <= 3)))),
      'any inf', bool(np.isinf(L).any()))
for i, nm in enumerate(['nan-start', 'flat', 'zeros', 'gaps', 'all-nan', 'inf/neg', 'flat-path', 'to-zero']):
    fv = np.argmax(np.isfinite(L[i])) if np.isfinite(L[i]).any() else -1
    print('  path %d %-9s first finite col %5d  NaN share %.3f  median L %.2f' % (
        i, nm, fv, np.isnan(L[i]).mean(), np.nanmedian(L[i]) if np.isfinite(L[i]).any() else np.nan))
c0 = close.copy()
L0 = R.target_levels(c0, rf); L0b = R.target_levels(c0, rf, None); L0c = R.target_levels(c0, rf, y10)
print('y10 ignored / None ok:', same(L0, L0b) and same(L0, L0c))
print('deterministic:', same(L0, R.target_levels(c0.copy(), rf.copy())))
for k in (1000.0, 1e-3, 1234.5):
    Lk = R.target_levels(c0 * k, rf)
    bit = np.array_equal(L0, Lk, equal_nan=True)
    diff = np.nanmax(np.abs(L0 - Lk)); nanmatch = np.array_equal(np.isnan(L0), np.isnan(Lk))
    flips = np.sum(np.round(np.nan_to_num(L0) / 0.5) != np.round(np.nan_to_num(Lk) / 0.5))
    print('scale x%g: bit-identical %s, NaN pattern same %s, max |diff| %.3g, 0.5-grid flips %d' % (k, bit, nanmatch, diff, flips))
# scale invariance on the edge-case array too
Lk = R.target_levels(np.array(c) * 1000.0, rf)
print('scale x1000 on edge-case array: bit-identical', np.array_equal(L, Lk, equal_nan=True), 'max|diff| %.3g' % np.nanmax(np.abs(L - Lk)))
# int / float32 input
print('float32 input ok:', R.target_levels(c0.astype(np.float32), rf).dtype)
# speed P=500, T=10000
g = np.random.default_rng(1)
cs = 100 * np.exp(np.cumsum(g.normal(0.0002, 0.011, (500, 10000)), axis=1))
t0 = time.time(); Ls = R.target_levels(cs, np.zeros_like(cs)); print('speed P=500 T=10000: %.2fs, shape %s' % (time.time() - t0, Ls.shape))

# ---------------- exact causality: 50 paths, 100 cut points --------------------------------------------------------
P = 50
cc = close[:P].copy(); cc[0, :800] = np.nan; cc[1, 1000:1200] = cc[1, 999]; cc[2, 200:260] = 0.0; cc[3, 1500] = np.nan
rr = rf[:P].copy(); yy = y10[:P].copy()
Lb = R.target_levels(cc, rr, yy)
cuts = sorted(set([0, 1, 2, 10, 120, 248, 249, 250, 251, 260, 298, 299, 300, 301, T - 3, T - 2, T - 1]
                  + list(g.integers(0, T, 100 - 17))))
while len(cuts) < 100: cuts = sorted(set(cuts + [int(g.integers(0, T))]))
nfail = 0; worst = None
for j, t in enumerate(cuts):
    c2 = cc.copy(); r2 = rr.copy(); y2 = yy.copy(); n = T - t - 1
    if n > 0:
        kind = j % 5
        if kind == 0:   # different random walk continuation
            c2[:, t + 1:] = cc[:, t:t + 1] * np.exp(np.cumsum(g.normal(0, 0.03, (P, n)), axis=1))
        elif kind == 1: # NaN
            c2[:, t + 1:] = np.nan
        elif kind == 2: # garbage: zeros, negatives, inf, huge, NaN mixed
            c2[:, t + 1:] = g.choice([0.0, -1.0, np.inf, -np.inf, 1e300, 1e-300, np.nan, 5.0], size=(P, n))
        elif kind == 3: # crash to near zero then flat
            c2[:, t + 1:] = 1e-12
        else:           # explosive growth
            c2[:, t + 1:] = cc[:, t:t + 1] * np.exp(np.cumsum(np.abs(g.normal(0, 0.2, (P, n))), axis=1))
        r2[:, t + 1:] = g.choice([np.nan, 1e9, -3.0, 0.0], size=(P, n))
        y2[:, t + 1:] = g.choice([np.nan, -50.0, 1e6], size=(P, n))
    with np.errstate(all='ignore'):
        L2 = R.target_levels(c2, r2, y2)
    a = Lb[:, :t + 1]; b = L2[:, :t + 1]
    ok = a.shape == b.shape and np.array_equal(a.view(np.int64), b.view(np.int64))
    if not ok:
        nfail += 1
        if worst is None: worst = (t, np.nanmax(np.abs(a - b)))
print('causality: %d cut points (min %d, max %d, %d below 300, %d >= T-3), failures %d %s' % (
    len(cuts), min(cuts), max(cuts), sum(1 for t in cuts if t < 300), sum(1 for t in cuts if t >= T - 3), nfail,
    '' if worst is None else 'first failure t=%d maxdiff %.3g' % worst))
print('AUDIT INTERFACE DONE')
