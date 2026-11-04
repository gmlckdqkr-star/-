"""AUDIT (lane D, TS2 r2): exact causality test of rule.target_levels.
50 synthetic paths; 100 cut points t (incl. t < 300 and near the end). Every column > t of close, rf and y10 is replaced
by a different random continuation (another path's continuation, NaN, zeros, inf, huge / negative garbage, noise).
Output columns <= t must be bit-identical."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import rule, sim

T = 7860; P = 50
d = sim.simulate(P, T, 4242, mechanism=True)
r, rf, y = d['r'], d['rf'], d['y10']
close = 1000.0 * np.cumprod(1 + r, axis=1)
close[0, :400] = np.nan; close[1, 2000:2300] = close[1, 1999]; close[2, :150] = 0.0      # edge cases in the base too
alt = sim.simulate(P, T, 4343, mechanism=False)
aclose = 3.0 * np.cumprod(1 + alt['r'], axis=1)
B0 = rule.target_levels(close, rf, y)
g = np.random.default_rng(99)
cuts = sorted(set([0, 1, 2, 5, 20, 100, 250, 297, 298, 299, 300, 301, 302, 303, 310, 7850, 7855, 7857, 7858, 7859]
                  + list(g.integers(0, T, 200))))[:0]
fixed = [0, 1, 2, 5, 20, 100, 250, 297, 298, 299, 300, 301, 302, 303, 310, 7850, 7855, 7857, 7858, 7859]
rand = [int(x) for x in g.choice(np.setdiff1d(np.arange(T), fixed), 80, replace=False)]
cuts = sorted(fixed + rand)
assert len(cuts) == 100
nfail = 0; worst = None
for i, t in enumerate(cuts):
    c, f, yy = close.copy(), rf.copy(), y.copy()
    mode = i % 5
    n = T - t - 1
    if n > 0:
        if mode == 0:      # another path's continuation
            c[:, t + 1:] = aclose[:, t + 1:] * 17.0; f[:, t + 1:] = alt['rf'][:, t + 1:] * 3; yy[:, t + 1:] = alt['y10'][:, t + 1:] + 5
        elif mode == 1:    # NaN everywhere
            c[:, t + 1:] = np.nan; f[:, t + 1:] = np.nan; yy[:, t + 1:] = np.nan
        elif mode == 2:    # garbage
            gar = g.choice(np.array([0.0, -5.0, 1e300, -1e300, np.inf, -np.inf, np.nan, 1e-300]), (P, n))
            c[:, t + 1:] = gar; f[:, t + 1:] = g.choice(np.array([0.0, 1e10, -1.0, np.nan, np.inf]), (P, n))
            yy[:, t + 1:] = g.normal(0, 1e6, (P, n))
        elif mode == 3:    # crash then huge rally
            c[:, t + 1:] = (np.nan_to_num(c[:, t:t + 1], nan=1.0) + 1.0) * np.exp(np.cumsum(g.normal(0, 0.2, (P, n)), axis=1))
            f[:, t + 1:] = g.uniform(0, 0.01, (P, n)); yy[:, t + 1:] = g.uniform(-2, 30, (P, n))
        else:              # zeros / flat
            c[:, t + 1:] = 0.0; f[:, t + 1:] = 0.0; yy[:, t + 1:] = 0.0
    with np.errstate(all='ignore'):
        B1 = rule.target_levels(c, f, yy)
    same = np.array_equal(B0[:, :t + 1], B1[:, :t + 1], equal_nan=True)
    if not same:
        nfail += 1
        bad = np.argwhere(~((B0[:, :t + 1] == B1[:, :t + 1]) | (np.isnan(B0[:, :t + 1]) & np.isnan(B1[:, :t + 1]))))
        worst = (t, mode, bad[:5].tolist())
        print('LEAK at cut', t, 'mode', mode, bad[:5].tolist(), flush=True)
    # sanity: the continuation does change later outputs (the test has power)
print('cuts tested:', len(cuts), 'min', min(cuts), 'max', max(cuts), 'n<300:', sum(t < 300 for t in cuts),
      'n>=7800:', sum(t >= 7800 for t in cuts))
print('causality failures:', nfail, worst)
# power check: continuation changes outputs after t
t = 3000; c = close.copy(); c[:, t + 1:] = aclose[:, t + 1:]
B1 = rule.target_levels(c, rf, y)
print('power check: columns > t differ on', int((B1[:, t + 1:] != B0[:, t + 1:]).any(axis=1).sum()), 'of', P, 'paths')
# cross-path independence: each path alone == batch
ind = all(np.array_equal(rule.target_levels(close[k:k + 1], rf[k:k + 1], y[k:k + 1])[0], B0[k], equal_nan=True) for k in range(0, P, 7))
print('per-path independence (every 7th path alone == batch):', ind)
