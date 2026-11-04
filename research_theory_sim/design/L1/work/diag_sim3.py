import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1')
import sim
np.seterr(all='ignore')
s = sim.simulate(500, 7860, seed=1, return_state=True)
r = s['r']; st = s['state']; p = s['params']
for i in (353, 30):
    lr = np.log1p(r[i]); wb = p['Phi'][i]/p['beta'][i]
    wr = st['w'][i]/wb
    f = np.where(~(wr < 5))[0]; t0 = f[0]
    print('path', i, 'first w/wbar>=5', t0)
    for t in range(max(t0-30,0), t0+25, 1):
        print(t, round(float(lr[t]),4), 'w/wbar', round(float(wr[t]),2), 'lev', round(float(st['lev'][i,t]),2), 'Lmax', round(float(st['Lmax'][i,t]),2), 'QS', round(float(st['QS'][i,t]),3), 'M', round(float(st['M'][i,t]),3))
