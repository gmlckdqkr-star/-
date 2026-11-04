"""AUDIT (blind auditor, lane A): exact causality (check 5) and engine-level scale invariance (check 4).
50 synthetic paths, 100 cut points (incl. t < 300 and the last 60 columns); every column > t of close, rf and y10
is replaced by a different random continuation (random walk, NaN, garbage, zeros, mixed); columns <= t must be
bit-identical."""
import sys, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np
import exec_engine as ee
import sim, rule

T = 7860; P = 50
out = {}
for mech, seed in ((True, 9191), (False, 9192)):
    w2 = sim.simulate(P, T, seed, mechanism=mech)
    cl = np.cumprod(1 + w2['r'], axis=1); rf2 = w2['rf'].copy(); y2 = w2['y10'].copy()
    # make some paths open late / have gaps so the NaN bookkeeping is exercised too
    cl[0, :400] = np.nan; cl[1, 1000:1010] = np.nan; cl[2, 2000:2100] = cl[2, 1999]
    Bf = rule.target_levels(cl, rf2, y2)
    g = np.random.default_rng(31337 + int(mech))
    lo = [0, 1, 2, 5, 50, 150, 298, 299] + list(g.choice(np.arange(3, 299), 8, replace=False))
    hi = [T - 2, T - 3, T - 5, T - 10] + list(g.choice(np.arange(T - 60, T - 10), 12, replace=False))
    mid = list(g.choice(np.arange(300, T - 60), 100 - len(set(lo)) - len(set(hi)), replace=False))
    cuts = sorted(set(lo) | set(hi) | set(mid))
    fails = []
    modes = ['randomwalk', 'nan', 'garbage', 'zeros', 'mixed']
    for i, t in enumerate(cuts):
        mode = modes[i % len(modes)]
        c2 = cl.copy(); r2 = rf2.copy(); yy2 = y2.copy(); n = T - t - 1
        if mode == 'randomwalk':
            c2[:, t + 1:] = np.nan_to_num(c2[:, t:t + 1], nan=1.0) * np.exp(np.cumsum(g.normal(0, 0.05, (P, n)), axis=1))
            r2[:, t + 1:] = g.uniform(-1, 1, (P, n)); yy2[:, t + 1:] = g.uniform(-50, 50, (P, n))
        elif mode == 'nan':
            c2[:, t + 1:] = np.nan; r2[:, t + 1:] = np.nan; yy2[:, t + 1:] = np.nan
        elif mode == 'garbage':
            c2[:, t + 1:] = g.choice([np.inf, -np.inf, -1.0, 1e300, 1e-300, 0.0, np.nan], (P, n))
            r2[:, t + 1:] = g.choice([np.inf, -5.0, np.nan, 1e10], (P, n)); yy2[:, t + 1:] = g.choice([np.inf, np.nan, -1e9], (P, n))
        elif mode == 'zeros':
            c2[:, t + 1:] = 0.0; r2[:, t + 1:] = 0.0; yy2[:, t + 1:] = 0.0
        else:
            c2[:, t + 1:] = np.nan_to_num(c2[:, t:t + 1], nan=1.0) * g.lognormal(0, 1.0, (P, n))
            m = g.uniform(size=(P, n)) < 0.2; tmp = c2[:, t + 1:]; tmp[m] = np.nan; c2[:, t + 1:] = tmp
            r2[:, t + 1:] = g.normal(0, 1, (P, n)); yy2[:, t + 1:] = g.normal(0, 100, (P, n))
        with np.errstate(all='ignore'):
            B2 = rule.target_levels(c2, r2, yy2)
        a, b = B2[:, :t + 1], Bf[:, :t + 1]
        ok = np.array_equal(a, b, equal_nan=True) and a.tobytes() == b.tobytes()
        if not ok: fails.append([int(t), mode])
    k = 'ON' if mech else 'OFF'
    out[k] = dict(n_cuts=len(cuts), cuts_lt300=int(sum(c < 300 for c in cuts)), cuts_last60=int(sum(c >= T - 60 for c in cuts)),
                  min_cut=int(min(cuts)), max_cut=int(max(cuts)), fails=fails, exact_ok=len(fails) == 0)
    print(k, out[k], flush=True)

# engine-level scale invariance on 2000 paths (fresh seed 10001, both worlds)
for mech in (True, False):
    w = sim.simulate(1000, T, 10001, mechanism=mech); r, rf = w['r'], w['rf']
    close = np.cumprod(1 + r, axis=1)
    B = rule.target_levels(close, rf)
    res = {}
    for s in (1000.0, 1e-4):
        Bs = rule.target_levels(close * s, rf)
        a = ee.run(r, rf, B); b = ee.run(r, rf, Bs)
        res['scale_%g' % s] = dict(B_maxabs=float(np.nanmax(np.abs(Bs - B))), B_bit_identical=bool(np.array_equal(Bs, B, equal_nan=True)),
                                   state_zero_pattern_same=bool(np.array_equal(Bs == 0, B == 0)),
                                   engine_cagr_identical=bool(np.array_equal(a['cagr'], b['cagr'])),
                                   n_paths_cagr_differs=int(np.sum(a['cagr'] != b['cagr'])))
    out['scale_engine_' + ('ON' if mech else 'OFF')] = res
    print('scale', mech, res, flush=True)
json.dump(out, open('/mnt/project-files/research/theory_sim/r2/design/A/audit/a_causality.json', 'w'), indent=1)
