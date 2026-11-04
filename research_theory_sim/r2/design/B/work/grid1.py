import sys, itertools, json, numpy as np
from lib import *
import fam
P = 400; seeds = [11, 12]
W = {}
for sd in seeds:
    for mech in (True, False):
        s, close = world(P, sd, mech); W[(sd, mech)] = (s, fam.feats(close, s['rf']), baselines(s))
def ev(name, **kw):
    res = {}; ex_on = []; ex_off = []; tpy = []
    for (sd, mech), (s, F, bl) in W.items():
        sm = score(fam.level(F, **kw), s); c = sm['cagr_med']; tpy.append(sm['trades_per_year_med'])
        res['%d_%s' % (sd, 'ON' if mech else 'OFF')] = round(c, 5)
        (ex_on if mech else ex_off).append(c - bl['best_const'])
    n = log_variant(name, kw, seeds, P, res)
    print('%3d %-8s %-70s dON=%+.4f dOFF=%+.4f tpy=%.1f' % (n, name, json.dumps(kw), np.mean(ex_on), np.mean(ex_off), np.mean(tpy)), flush=True)
    return np.mean(ex_on), np.mean(ex_off)
if __name__ == '__main__':
    for (sd, mech), (s, F, bl) in W.items(): print(sd, mech, {k: round(v, 4) for k, v in bl.items() if k in ('hold1', 'best_const', 'best_const_level')})
    for hfwd in (20, 40, 160):
        for k in (0.35, 0.5, 0.75):
            ev('vol', k=k, hfwd=hfwd)
