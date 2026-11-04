import sys, json, numpy as np
from lib import *
import fam
P = 500; seeds = [21, 22, 23, 24]
W = {}
for sd in seeds:
    for mech in (True, False):
        s, close = world(P, sd, mech); W[(sd, mech)] = (s, fam.feats(close, s['rf']), baselines(s))
hb = {m: np.mean([W[(sd, m)][2]['hold1'] - W[(sd, m)][2]['best_const'] for sd in seeds]) for m in (True, False)}
print('hold1 - best_const: ON %+.4f OFF %+.4f' % (hb[True], hb[False]))
print('best const levels', [(sd, m, W[(sd, m)][2]['best_const_level']) for (sd, m) in W])
C = {'C0': dict(k=0.6, hfwd=20), 'C1': dict(k=0.6, hfwd=20, bh=0.1, hy=1), 'C2': dict(k=0.6, hfwd=20, bh=0.1, hy='y1'),
     'C3': dict(k=0.6, hfwd=20, bh=0.2, hy='y1'), 'C4': dict(k=0.5, hfwd=20)}
for name, kw in C.items():
    res = {}; d = {True: [], False: []}; rob = {True: [], False: []}
    for (sd, mech), (s, F, bl) in W.items():
        Lv = fam.level(F, **kw)
        c = score(Lv, s)['cagr_med']; res['%d_%s' % (sd, mech)] = round(c, 5); d[mech].append(c - bl['best_const'])
    n = log_variant('val1_' + name, kw, seeds, P, res)
    print('%3d %s %-50s dON=%+.4f dOFF=%+.4f  min=%+.4f  per-seed ON %s' % (n, name, json.dumps(kw), np.mean(d[True]), np.mean(d[False]),
          min(np.mean(d[True]), np.mean(d[False])), np.round(d[True], 4)), flush=True)
