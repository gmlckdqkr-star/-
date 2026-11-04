import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule
T = 7860; P = 50
s = sim.simulate(P, T, 4242, True); s2 = sim.simulate(P, T, 4243, False)
close = 100.0 * np.exp(np.cumsum(np.log1p(s['r']), axis=1)); rf = s['rf'].copy(); y10 = s['y10'].copy()
alt_close = 37.0 * np.exp(np.cumsum(np.log1p(s2['r']), axis=1)); alt_rf = s2['rf']; alt_y = s2['y10']
base = rule.target_levels(close, rf, y10)
g = np.random.default_rng(99)
cuts = np.unique(np.concatenate([[0, 1, 5, 30, 59, 60, 61, 120, 250, 299, 300, 301, T - 3, T - 2], g.integers(0, 300, 16), g.integers(300, T - 1, 70)]))[:100]
while len(cuts) < 100:
    cuts = np.unique(np.concatenate([cuts, g.integers(300, T - 1, 100 - len(cuts))]))
bad = 0; t0 = time.time()
for i, t in enumerate(cuts):
    c2 = close.copy(); f2 = rf.copy(); y2 = y10.copy()
    mode = i % 5
    if mode == 0:   # different random continuation (another world, rescaled)
        c2[:, t + 1:] = alt_close[:, t + 1:]; f2[:, t + 1:] = alt_rf[:, t + 1:]; y2[:, t + 1:] = alt_y[:, t + 1:]
    elif mode == 1: # NaN future
        c2[:, t + 1:] = np.nan; f2[:, t + 1:] = np.nan; y2[:, t + 1:] = np.nan
    elif mode == 2: # garbage: huge, negative, zero, inf mixed
        n = T - t - 1
        garb = g.choice(np.array([0.0, -1.0, 1e300, np.inf, -np.inf, np.nan, 1e-300, 5.0]), size=(P, n))
        c2[:, t + 1:] = garb; f2[:, t + 1:] = g.choice(np.array([np.nan, 1e10, -5.0, 0.0, np.inf]), size=(P, n)); y2[:, t + 1:] = garb
    elif mode == 3: # random-walk continuation with wild vol and rates
        n = T - t - 1
        c2[:, t + 1:] = close[:, [t]] * np.exp(np.cumsum(g.normal(0, 0.08, (P, n)), axis=1)); f2[:, t + 1:] = g.uniform(-0.01, 0.01, (P, n)); y2[:, t + 1:] = g.uniform(-50, 50, (P, n))
    else:           # flat / zeros
        c2[:, t + 1:] = 0.0; f2[:, t + 1:] = 0.5; y2[:, t + 1:] = 0.0
    with np.errstate(all='ignore'):
        o = rule.target_levels(c2, f2, y2)
    same = np.array_equal(base[:, :t + 1], o[:, :t + 1], equal_nan=True)
    # bitwise including NaN payloads
    same_bits = np.array_equal(base[:, :t + 1].view(np.uint64), o[:, :t + 1].view(np.uint64))
    changed_after = not np.array_equal(base[:, t + 1:], o[:, t + 1:], equal_nan=True) if t + 1 < T else None
    if not (same and same_bits): bad += 1; print('LEAK at t=%d mode %d' % (t, mode))
print('cuts tested', len(cuts), 'n<300:', int((cuts < 300).sum()), 'max cut', int(cuts.max()), 'leaks', bad, 'time %.0fs' % (time.time() - t0))
