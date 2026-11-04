import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
base = dict(m0=0.08, kf=0.5, A=1.0, ns=42, sv=60, B=0.5, nl=504)
sweeps = [('A', (0.5, 0.75, 1.25, 1.5)), ('ns', (63, 84)), ('B', (0.25, 1.0)), ('nl', (252, 756)), ('sv', (120,)), ('m0', (0.07, 0.10))]
for k, vals in sweeps:
    for v in vals:
        p = dict(base); p[k] = v
        o = h.evaluate(c.F_kelly, p, 'F5_coord')
        print(o['N'], p, {kk: round(vv, 4) for kk, vv in o.items() if kk != 'N'}, flush=True)
