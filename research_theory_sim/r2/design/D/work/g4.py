import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(1200, 1)
b = dict(f=1.25, hv=60, p=1.5)
for a in (0.5, 1.0, 2.0):
    evaluate(W, 's4carry', a_s=a, s0=0.01, **b)
for a in (1.0, 2.0):
    evaluate(W, 's4carry', a_s=a, s0=0.01, hs=1260, **b)
for q in (-1.0, 0.5, 1.0, 2.0):
    evaluate(W, 's4ledger', q=q, hx=500, **b)
evaluate(W, 's4ledger', q=1.0, hx=250, **b)
for a in (0.5, 1.0):
    evaluate(W, 's4rate', a_r=a, wr=250, **b)
for n0 in (20, 50):
    evaluate(W, 's4prem', n0=n0, **b)
