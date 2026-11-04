import sys, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c
for sv, A, ns, B, m0 in itertools.product((20, 60), (1.0, 2.0, 3.0), (21, 42), (0.0, 0.5), (0.06, 0.08)):
    p = dict(m0=m0, kf=0.5, A=A, ns=ns, sv=sv)
    if B: p.update(B=B, nl=504)
    o = h.evaluate(c.F_kelly, p, 'F4_mom_rev')
    print(o['N'], p, {k: round(v, 4) for k, v in o.items() if k != 'N'}, flush=True)
