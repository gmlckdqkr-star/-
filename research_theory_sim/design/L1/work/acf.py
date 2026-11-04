import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1')
import sim
np.seterr(all='ignore')
P, T = 1000, 7860
for mech in (True, False):
    s = sim.simulate(P, T, seed=1, mechanism=mech)
    lr = np.log1p(s['r'][:, 300:]); lr = lr - lr.mean(1, keepdims=True)
    v = (lr ** 2).mean(1)
    ac = [np.median((lr[:, k:] * lr[:, :-k]).mean(1) / v) for k in (1, 2, 3, 5, 10, 20)]
    print('mech', mech, 'acf lags 1,2,3,5,10,20', np.round(ac, 3))
    cp = np.cumsum(lr, 1)
    vr = []
    for h in (5, 21, 63, 126, 252, 504):
        d = cp[:, h:] - cp[:, :-h]
        vr.append(np.median(d.var(1) / (h * v)))
    print('   variance ratio h=5,21,63,126,252,504', np.round(vr, 3))
