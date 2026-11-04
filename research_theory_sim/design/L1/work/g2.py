import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
for ns in (21, 63, 126):
    for A in (0.5, 1.0, 2.0, 4.0):
        p = dict(m0=0.06, kf=0.5, A=A, ns=ns)
        o = h.evaluate(c.F_kelly, p, 'F2_momentum')
        print(o['N'], p, {k: round(v, 4) for k, v in o.items() if k != 'N'}, flush=True)
