"""AUDIT (blind auditor, lane A): rule.py interface (check 4) and exact causality (check 5). Synthetic data only."""
import sys, time, json, ast, inspect
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np
import sim, rule

out = {}
# --- imports / names / signature
src = open('/mnt/project-files/research/theory_sim/r2/design/A/rule.py').read()
tree = ast.parse(src)
imps = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Import): imps |= {a.name for a in n.names}
    if isinstance(n, ast.ImportFrom): imps.add(n.module)
out['imports'] = sorted(imps)
out['imports_ok'] = imps <= {'numpy', 'math'}
bad_calls = [w for w in ('open(', 'eval(', 'exec(', '__import__', 'os.', 'sys.', 'np.load', 'np.save', 'tofile', 'fromfile', 'random') if w in src]
out['suspicious_tokens'] = bad_calls
out['INPUTS'] = list(rule.INPUTS); out['PARAMS'] = rule.PARAMS; out['n_params'] = len(rule.PARAMS)
out['signature'] = str(inspect.signature(rule.target_levels))
out['PARAMS_is_literal'] = any(isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'PARAMS' for t in n.targets)
                               and isinstance(n.value, ast.Dict) for n in tree.body)
out['docstring_lines'] = len((rule.__doc__ or '').strip().splitlines())

T = 7860
w = sim.simulate(60, T, 4242, mechanism=True)
close = np.cumprod(1 + w['r'], axis=1); rf = w['rf']; y10 = w['y10']
c0, r0, y0 = close.copy(), rf.copy(), y10.copy()
B = rule.target_levels(close, rf, y10)
out['inputs_unmodified'] = bool(np.array_equal(c0, close) and np.array_equal(r0, rf) and np.array_equal(y0, y10))
out['shape'] = list(B.shape); out['dtype'] = str(B.dtype)
fin = B[np.isfinite(B)]
out['range'] = [float(fin.min()), float(fin.max())]; out['in_0_3'] = bool(fin.min() >= 0 and fin.max() <= 3)
out['nan_count'] = int(np.isnan(B).sum()); out['inf_count'] = int(np.isinf(B).sum())
out['y10_None_same'] = bool(np.array_equal(rule.target_levels(close, rf), B, equal_nan=True))
out['deterministic'] = bool(np.array_equal(rule.target_levels(close, rf, y10), B, equal_nan=True))
# params=None and explicit PARAMS
out['params_explicit_same'] = bool(np.array_equal(rule.target_levels(close, rf, y10, params=dict(rule.PARAMS)), B, equal_nan=True))

# --- scale invariance
for s in (1000.0, 1e-3, 1234.5, 7.0e6):
    Bs = rule.target_levels(close * s, rf, y10)
    out['scale_%g_bit_identical' % s] = bool(np.array_equal(Bs, B, equal_nan=True))
    out['scale_%g_maxabs' % s] = float(np.nanmax(np.abs(Bs - B)))
    # does the discretised level the engine would hold differ? (0.5 grid)
    out['scale_%g_rounded_identical' % s] = bool(np.array_equal(np.round(np.nan_to_num(Bs, nan=0) * 2), np.round(np.nan_to_num(B, nan=0) * 2)))
    out['scale_%g_nan_pattern_same' % s] = bool(np.array_equal(np.isnan(Bs), np.isnan(B)))
    # state flips (level 0 vs base)
    out['scale_%g_zero_pattern_same' % s] = bool(np.array_equal(Bs == 0, B == 0))

# --- NaN / zero / flat / garbage stretches in close
c = close.copy()
c[0, :500] = np.nan                    # not yet opened
c[1, :800] = 0.0                       # zeros before opening
c[2, 300:900] = c[2, 299]              # flat stretch
c[3, 1000:1020] = np.nan               # holiday gap
c[4, 2000:2005] = 0.0                  # bad zeros
c[5, :] = 1.0                          # never moves
c[6, :] = np.nan                       # never opens
c[7, 4000:4003] = -5.0                 # negative garbage
c[8, 5000] = np.inf                    # inf garbage
c[9, :7000] = np.nan                   # opens late
try:
    Bn = rule.target_levels(c, rf, y10); ok = True
except Exception as e:
    Bn = None; ok = False; out['nan_error'] = repr(e)
out['nan_zero_flat_no_crash'] = ok
if ok:
    f = Bn[np.isfinite(Bn)]
    out['nan_case_range'] = [float(f.min()), float(f.max())]
    out['nan_case_inf'] = int(np.isinf(Bn).sum())
    out['row5_constant_close_all_nan'] = bool(np.isnan(Bn[5]).all())
    out['row6_all_nan_close_all_nan'] = bool(np.isnan(Bn[6]).all())
    out['row9_nan_before_7000'] = bool(np.isnan(Bn[9, :7000]).all()); out['row9_finite_after_7001'] = bool(np.isfinite(Bn[9, 7002:]).all())
    out['row0_nan_before_open'] = bool(np.isnan(Bn[0, :501]).all())
    out['rows_10plus_unchanged'] = bool(np.array_equal(Bn[10:], B[10:], equal_nan=True))
    out['row2_finite_after_flat'] = bool(np.isfinite(Bn[2, 300:]).all())
    out['row3_after_gap_finite'] = bool(np.isfinite(Bn[3, 1000:]).all())
# 1-D input
try:
    b1 = rule.target_levels(close[0], rf[0]); out['oned_shape'] = list(b1.shape)
except Exception as e:
    out['oned_error'] = repr(e)
# rf / y10 with NaN do not crash
rfn = rf.copy(); rfn[:, :100] = np.nan
out['rf_nan_no_change'] = bool(np.array_equal(rule.target_levels(close, rfn, None), B, equal_nan=True))

# --- speed P=500, T=10000
g = np.random.default_rng(5); rr = g.standard_t(5, (500, 10000)) * 0.008; rr[:, 0] = 0
cc = np.cumprod(1 + rr, axis=1); ff = np.full((500, 10000), 1e-4); yy = np.full((500, 10000), 4.0)
t0 = time.time(); _ = rule.target_levels(cc, ff, yy); out['speed_P500_T10000_s'] = round(time.time() - t0, 2)

# --- exact causality: 50 paths, 100 cut points incl. t < 300 and near the end
P = 50
w2 = sim.simulate(P, T, 9191, mechanism=True)
cl = np.cumprod(1 + w2['r'], axis=1); rf2 = w2['rf'].copy(); y2 = w2['y10'].copy()
Bf = rule.target_levels(cl, rf2, y2)
g = np.random.default_rng(31337)
cuts = sorted(set([0, 1, 2, 5, 50, 150, 299, 300, 301, T - 3, T - 2] +
                  list(g.integers(3, 300, 12)) + list(g.integers(T - 60, T - 1, 12)) + list(g.integers(301, T - 60, 200))))[:100]
if len(cuts) < 100:
    extra = [c for c in range(302, T - 60, 37) if c not in cuts]
    cuts = sorted(cuts + extra[:100 - len(cuts)])
fails = []
modes = ['randomwalk', 'nan', 'garbage', 'zeros', 'mixed']
for i, t in enumerate(cuts):
    mode = modes[i % len(modes)]
    c2 = cl.copy(); r2 = rf2.copy(); yy2 = y2.copy()
    n = T - t - 1
    if n <= 0: continue
    if mode == 'randomwalk':
        c2[:, t + 1:] = c2[:, t:t + 1] * np.exp(np.cumsum(g.normal(0, 0.05, (P, n)), axis=1))
        r2[:, t + 1:] = g.uniform(-1, 1, (P, n)); yy2[:, t + 1:] = g.uniform(-50, 50, (P, n))
    elif mode == 'nan':
        c2[:, t + 1:] = np.nan; r2[:, t + 1:] = np.nan; yy2[:, t + 1:] = np.nan
    elif mode == 'garbage':
        c2[:, t + 1:] = g.choice([np.inf, -np.inf, -1.0, 1e300, 1e-300, 0.0, np.nan], (P, n))
        r2[:, t + 1:] = g.choice([np.inf, -5.0, np.nan, 1e10], (P, n)); yy2[:, t + 1:] = g.choice([np.inf, np.nan, -1e9], (P, n))
    elif mode == 'zeros':
        c2[:, t + 1:] = 0.0; r2[:, t + 1:] = 0.0; yy2[:, t + 1:] = 0.0
    else:
        c2[:, t + 1:] = c2[:, t:t + 1] * g.lognormal(0, 1.0, (P, n))
        m = g.uniform(size=(P, n)) < 0.2; tmp = c2[:, t + 1:]; tmp[m] = np.nan; c2[:, t + 1:] = tmp
        r2[:, t + 1:] = g.normal(0, 1, (P, n)); yy2[:, t + 1:] = g.normal(0, 100, (P, n))
    with np.errstate(all='ignore'):
        B2 = rule.target_levels(c2, r2, yy2)
    same = np.array_equal(B2[:, :t + 1], Bf[:, :t + 1], equal_nan=True)
    # bit-identical: compare raw bytes too (distinguishes -0.0 / NaN payloads)
    same_bytes = B2[:, :t + 1].tobytes() == Bf[:, :t + 1].tobytes()
    if not (same and same_bytes): fails.append([int(t), mode, bool(same), bool(same_bytes)])
out['causality_n_cuts'] = len(cuts); out['causality_cuts_lt300'] = int(sum(c < 300 for c in cuts))
out['causality_cuts_last60'] = int(sum(c >= T - 60 for c in cuts)); out['causality_fails'] = fails
out['causality_exact_ok'] = len(fails) == 0
print(json.dumps(out, indent=1))
json.dump(out, open('/mnt/project-files/research/theory_sim/r2/design/A/audit/a_interface.json', 'w'), indent=1)
