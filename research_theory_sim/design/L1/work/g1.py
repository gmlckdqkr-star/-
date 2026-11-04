import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
res = []
for m0 in (0.06, 0.08):
    for nl in (126, 252, 504):
        for B in (0.5, 1.0, 2.0):
            p = dict(m0=m0, kf=0.5, B=B, nl=nl)
            o = h.evaluate(c.F_kelly, p, 'F1_reversal')
            print(o['N'], p, {k: round(v, 4) for k, v in o.items() if k != 'N'}, flush=True)
