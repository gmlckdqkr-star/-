import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
base = dict(m0=0.08, kf=0.5, A=1.0, ns=42, sv=60, B=0.5, nl=504)
combos = [dict(A=1.25, nl=252), dict(A=1.25, nl=252, sv=120), dict(A=1.25, nl=252, sv=120, m0=0.10), dict(A=1.25, sv=120),
          dict(A=1.5, sv=120, nl=252), dict(A=1.0, nl=252, sv=120, m0=0.10), dict(A=1.25, nl=252, B=0.75),
          dict(A=1.5, nl=252, B=0.75, sv=120), dict(ns=63, A=1.5, nl=252, sv=120)]
for cmb in combos:
    p = dict(base); p.update(cmb)
    o = h.evaluate(c.F_kelly, p, 'F6_combo')
    print(o['N'], p, {kk: round(vv, 4) for kk, vv in o.items() if kk != 'N'}, flush=True)
