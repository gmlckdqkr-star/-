import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
base = dict(m0=0.08, kf=0.5, A=1.5, ns=42, sv=120, B=0.75, nl=252)   # N119
for G, mhl in ((0.02, 252), (0.05, 252), (0.05, 504), (-0.03, 252)):
    p = dict(base, G=G, mhl=mhl)
    o = h.evaluate(c.F_kelly_gap, p, 'F7_ratchetgap')
    print(o['N'], p, {kk: round(vv, 4) for kk, vv in o.items() if kk != 'N'}, flush=True)
