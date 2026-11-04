import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
seed = int(sys.argv[1])
W = worlds(2000, seed)
print('BASE seed', seed, 'ON', W[True]['base'], 'OFF', W[False]['base'], flush=True)
b = dict(f=1.25, hv=60, p=1.5)
tg = 's5_seed%d' % seed
evaluate(W, tg, **b)
evaluate(W, tg, f=1.0, hv=60, p=2.0)
evaluate(W, tg, f=1.5, hv=60, p=1.0)
for a in (0.5, 1.0, 1.5):
    evaluate(W, tg, a_s=a, s0=0.01, **b)
for q, hx in ((1.0, 500), (2.0, 500), (3.0, 500), (2.0, 250), (2.0, 1000), (-1.0, 500)):
    evaluate(W, tg, q=q, hx=hx, **b)
evaluate(W, tg, a_s=1.0, s0=0.01, q=2.0, hx=500, **b)
