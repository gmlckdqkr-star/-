import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
for m0 in (0.04, 0.06, 0.08, 0.10, 0.12):
    p = dict(m0=m0, kf=0.5)
    o = h.evaluate(c.F_kelly, p, 'F0_voltarget')
    print(o['N'], p, {k: round(v, 4) for k, v in o.items() if k != 'N'})
