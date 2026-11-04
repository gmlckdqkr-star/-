import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np, sim
s = sim.simulate(500, 7860, 1, mechanism=True, record=True)
txt, d = sim.describe(s)
bad = (d['prem'] > 0.15) | (d['ac2'] > 0.3) | (d['mdd'] < -0.95)
print('bad frac', bad.mean())
p = s['params']
for k in ['k0','a_v','c','h_g','S0','lam_norm','h_M','b','a_dn','a_up','zeta','psi','scale']:
    print('%10s bad %.4g  good %.4g' % (k, np.median(p[k][bad]), np.median(p[k][~bad])))
h = s['hist']
i = np.where(bad)[0][:5]
for j in i:
    print(j, 'S max %.3f W max %.3f m range %.2f %.2f prem %.2f ac2 %.2f mdd %.2f' % (h['S'][j].max(), h['W'][j].max(), h['m'][j].min(), h['m'][j].max(), d['prem'][j], d['ac2'][j], d['mdd'][j]))
# gain proxy
gain = p['psi']*p['S0']*(p['lam_norm']-1)
print('gain bad', np.percentile(gain[bad],[10,50,90]), 'good', np.percentile(gain[~bad],[10,50,90]))
