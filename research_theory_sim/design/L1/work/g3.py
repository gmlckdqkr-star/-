import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
for ns in (21, 42, 63, 126, 252):
    for m0 in (0.06, 0.08, 0.10):
        p = dict(m0=m0, kf=0.5, ns=ns)
        o = h.evaluate(c.F_filter, p, 'F3_trendfilter')
        print(o['N'], p, {k: round(v, 4) for k, v in o.items() if k != 'N'}, flush=True)
