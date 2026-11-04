import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1')
import sim
s = sim.simulate(500, 7860, seed=1, return_state=True)
r = s['r']; st = s['state']; p = s['params']
bad = ~np.isfinite(r).all(axis=1)
print('nonfinite paths', bad.sum())
lr = np.log1p(r[:, 300:])
vol = lr.std(axis=1)*np.sqrt(252)
print('vol pct', np.percentile(vol, [1,10,50,90,99]).round(3))
wr = st['w'] / (p['Phi']/p['beta'])[:, None]
print('max w/wbar pct', np.percentile(wr.max(axis=1), [10,50,90,99]).round(2))
print('max QS pct', np.percentile(st['QS'].max(axis=1), [10,50,90,99]).round(3))
print('share days clipped', np.mean(np.abs(lr) >= 0.2499))
hi = np.argsort(vol)[-5:]
for i in hi:
    print(i, round(vol[i],3), {k: round(float(p[k][i]),3) for k in ('beta','Phi','phi_v','phi_f','H_min','h_k','c','kappa','tau_L','b_X')})
