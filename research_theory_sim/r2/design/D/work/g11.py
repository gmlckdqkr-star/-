import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(2000, 2)
print('BASE seed2 ON', W[True]['base'], 'OFF', W[False]['base'], flush=True)
tg = 's11_seed2'
for c in (1.0, 1.25, 1.5):
    evaluate(W, tg, trk=0.35, const=c)
evaluate(W, tg, trk=0.5, const=1.25)
evaluate(W, tg, trk=0.25, const=1.25)
for a in (0.5, 1.0):
    evaluate(W, tg, trk=0.35, f=1.032, p=0.0, kon=False, a_s=a, s0=0.01, hsm=120)
evaluate(W, tg, trk=0.5, f=1.032, p=0.0, kon=False, a_s=0.5, s0=0.01, hsm=120)
