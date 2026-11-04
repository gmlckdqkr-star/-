"""exploratory: which causal features predict forward excess returns in the ON and OFF worlds (selection seeds only)."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim
T = 7860; P = int(sys.argv[1]); seed = int(sys.argv[2])
def ewm(a, h):
    lam = 1 - 0.5 ** (1 / h); out = np.empty_like(a); s = a[:, 0].copy()
    for t in range(a.shape[1]):
        s = s + lam * (a[:, t] - s); out[:, t] = s
    return out
for mech in (True, False):
    S = sim.simulate(P, T, seed, mech)
    x = np.log1p(S['r']); rfa = S['rf'] * 252
    ab = 1.25 * np.sqrt(252) * np.abs(x)
    E = {h: ewm(ab, h) for h in (5, 10, 20, 40, 80, 160, 320)}
    M = {y: ewm(252 * x - rfa, 252 * y) for y in (1, 3, 6)}
    feats = {}
    for h1, h2 in ((5, 40), (10, 40), (20, 80), (40, 160), (80, 320), (10, 160), (20, 320)):
        feats['lv%d_%d' % (h1, h2)] = np.log(E[h1] / E[h2])
    for y in (1, 3, 6):
        feats['m%dy' % y] = M[y]
    rfs = np.zeros_like(rfa); rfs[:, 252:] = rfa[:, 252:] - rfa[:, :-252]; feats['drf1y'] = rfs
    feats['lvol320'] = np.log(E[320])
    ex = x - S['rf']
    cs = np.concatenate([np.zeros((P, 1)), np.cumsum(ex, axis=1)], axis=1)
    print('==== mechanism', mech)
    for H in (21, 63, 252):
        t0, t1 = 400, T - H - 4
        idx = np.arange(t0, t1, 5)
        fwd = (cs[:, idx + 3 + H] - cs[:, idx + 3]) * 252 / H     # annualised forward excess log return, after 2-day delay
        vnow = E[40][:, idx]
        row = []
        for k, f in feats.items():
            fv = f[:, idx]
            # per-path demeaned (within-path) correlation, pooled
            fd = fv - fv.mean(1, keepdims=True); yd = fwd - fwd.mean(1, keepdims=True)
            c = (fd * yd).sum() / np.sqrt((fd ** 2).sum() * (yd ** 2).sum())
            beta = (fd * yd).sum() / (fd ** 2).sum()
            row.append('%s:%+.3f(b%+.3f)' % (k, c, beta))
        print(' H=%3d ' % H + ' '.join(row))
