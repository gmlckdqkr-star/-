import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(1200, 1)
print('BASE ON', W[True]['base'], 'OFF', W[False]['base'], flush=True)
b = dict(f=1.25, hv=60, p=1.5)
evaluate(W, 's3', **b)
for p, f in ((1.0, 1.5), (2.0, 1.0), (2.0, 1.25), (1.5, 1.0), (1.5, 1.5)):
    evaluate(W, 's3', f=f, hv=60, p=p)
evaluate(W, 's3', f=1.25, hv=40, p=1.5)
evaluate(W, 's3', f=1.25, hv=90, p=1.5)
evaluate(W, 's3', est='abs', **b)
for Lm in (2.0, 2.5):
    evaluate(W, 's3', Lmax=Lm, **b)
