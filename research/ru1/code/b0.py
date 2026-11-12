import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru, beng
assert ru.WARM == beng.WARM, (ru.WARM, beng.WARM)
t0 = time.time(); B = ac3.prep(); print('prep', round(time.time() - t0, 1), flush=True)
out = {}
for bn in ('real_ndx_86_14', 'dev250_path', 'real_spx_55_85'):
    b = B[bn]; P, T = b['R'].shape; n = T - ru.WARM
    o, EU, EK = ru.acctP(b['R'], b['RF'], b['L'], np.ones((P, T)), np.zeros((P, n)), 0, 0, 0.0, .003, .22, .25, .0245, 1.0)
    s, _ = ru.stats(o[:, 0], EU, n / 252); out[bn] = s; print(bn, s, 'trades/yr', float(np.median(o[:, 4]) / (n / 252)), flush=True)
json.dump(out, open('/mnt/project-files/research/ru1/results/b0.json', 'w'), indent=1)
