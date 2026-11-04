import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(2000, 1)
print('BASE ON', W[True]['base'], 'OFF', W[False]['base'], flush=True)
tg = 's7'
for c in (1.0, 1.5, 2.0):
    evaluate(W, tg, trk=0.25, const=c)
for p in (1.0, 1.5, 2.0):
    for f in (0.75, 1.0, 1.25):
        evaluate(W, tg, trk=0.25, f=f, hv=60, p=p)
