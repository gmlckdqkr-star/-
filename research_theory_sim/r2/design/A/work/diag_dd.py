import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np, sim
s = sim.simulate(1000, 7860, 2, mechanism=True)
txt, d = sim.describe(s)
p = s['params']
G = p['psi']*p['S0']
q = np.quantile(G, [0, .25, .5, .75, 1])
for i in range(4):
    m = (G >= q[i]) & (G <= q[i+1])
    print('G %.3f-%.3f  P(dd<-.5) %.2f P(dd<-.75) %.2f medDD %.2f skew %.2f kurt %.1f ac2 %.3f' % (q[i], q[i+1], np.mean(d['mdd'][m]<=-.5), np.mean(d['mdd'][m]<=-.75), np.median(d['mdd'][m]), np.median(d['skew'][m]), np.median(d['kurt'][m]), np.median(d['ac2'][m])))
for k in ['a_dn','c','a_v','h_M','lam_norm']:
    v = p[k]; qq = np.quantile(v,[0,.5,1])
    for lo,hi in [(qq[0],qq[1]),(qq[1],qq[2])]:
        m=(v>=lo)&(v<=hi)
        print('%8s %.4f-%.4f P(dd<-.5) %.2f P(dd<-.75) %.2f' % (k, lo, hi, np.mean(d['mdd'][m]<=-.5), np.mean(d['mdd'][m]<=-.75)))
