import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1')
import sim
np.seterr(all='ignore')
s = sim.simulate(500, 7860, seed=1, return_state=True)
r = s['r']; st = s['state']; p = s['params']
for i in (353, 30):
    lr = np.log1p(r[i]); 
    f = np.where(~np.isfinite(lr))[0]
    t0 = f[0] if len(f) else None
    print('path', i, 'first nonfinite', t0)
    wb = p['Phi'][i]/p['beta'][i]
    for t in range(max(t0-40,0), t0+1, 2):
        print(t, round(float(lr[t]),4), 'w/wbar', round(float(st['w'][i,t]/wb),2), 'lev', round(float(st['lev'][i,t]),2), 'Lmax', round(float(st['Lmax'][i,t]),2), 'QS', round(float(st['QS'][i,t]),3), 'M', round(float(st['M'][i,t]),3))
