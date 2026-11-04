"""exploratory (selection seeds): forward excess return vs features, centred with the TRUE per-path premium
(analysis only; removes the finite-path demeaning bias). Also the conditional forward variance."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim
T = 7860; P = int(sys.argv[1]); seed = int(sys.argv[2])
def ewm(a, h):
    lam = 1 - 0.5 ** (1 / h); out = np.empty_like(a); s = a[:, :20].mean(1)
    for t in range(a.shape[1]):
        s = s + lam * (a[:, t] - s); out[:, t] = s
    return out
for mech in (True, False):
    S = sim.simulate(P, T, seed, mech); pr = S['params']
    x = np.log1p(S['r']); rfa = S['rf'] * 252
    ab = 1.25 * np.sqrt(252) * np.abs(x)
    E = {h: ewm(ab, h) for h in (10, 20, 40, 80, 160, 320)}
    mlog = (pr['mu'] - pr['sigma'] ** 2 / 2)[:, None]
    M = {y: ewm(252 * x - rfa, 252 * y) - mlog for y in (1, 3, 6)}
    feats = {}
    for h1, h2 in ((10, 40), (20, 80), (40, 160), (80, 320), (20, 320)):
        feats['lv%d_%d' % (h1, h2)] = np.log(E[h1] / E[h2])
    for y in (1, 3, 6):
        feats['m%dy' % y] = M[y]
    feats['lv80_sig'] = np.log(E[80] / pr['sigma'][:, None])
    ex = x - S['rf']
    cs = np.concatenate([np.zeros((P, 1)), np.cumsum(ex, axis=1)], axis=1)
    print('==== mechanism', mech)
    for H in (21, 63, 252):
        idx = np.arange(400, T - H - 4, 5)
        fwd = (cs[:, idx + 3 + H] - cs[:, idx + 3]) * 252 / H - mlog
        row = []
        for k, f in feats.items():
            fv = f[:, idx]; fd = fv - fv.mean(); yd = fwd
            c = (fd * yd).sum() / np.sqrt((fd ** 2).sum() * ((yd - yd.mean()) ** 2).sum())
            beta = (fd * yd).sum() / (fd ** 2).sum()
            row.append('%s:%+.3f(b%+.3f)' % (k, c, beta))
        print(' H=%3d ' % H + ' '.join(row))
