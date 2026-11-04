import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np, sim
s = sim.simulate(500, 7860, 1, mechanism=True, record=True)
txt, d = sim.describe(s)
h = s['hist']; r = s['r']; p = s['params']
for j in [int(a) for a in sys.argv[1:]]:
    lr = np.log1p(r[j]); 
    v = np.sqrt(np.convolve(lr**2, np.ones(63)/63, 'same')*252)
    print('path', j, {k: round(float(p[k][j]),4) for k in ['k0','a_v','c','h_g','S0','lam_norm','h_M','b','a_dn','a_up','zeta','psi','scale','sigma']})
    print(' ac2 %.2f mdd %.2f kurt %.1f' % (d['ac2'][j], d['mdd'][j], d['kurt'][j]))
    for t in range(300, 7860, 252):
        print('  y%2d vol63 %.2f S %.3f W %.3f m %+.2f dSabs %.4f cum %+.2f' % ((t-300)//252, v[t], h['S'][j,t], h['W'][j,t], h['m'][j,t], np.abs(h['dS'][j,t-252:t]).mean(), lr[300:t].sum()))
