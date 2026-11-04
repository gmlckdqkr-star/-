import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(2000, 1)
tg = 's9'
for th in (0.15, 0.35):
    evaluate(W, tg, trk=th, const=1.25)
for a in (0.5, 1.0):
    evaluate(W, tg, trk=0.25, f=1.0, p=0.0, a_s=a, s0=0.01, hsm=120)
evaluate(W, tg, trk=0.35, f=1.0, p=0.0, a_s=1.0, s0=0.01, hsm=120)
evaluate(W, tg, trk=0.25, f=1.25, p=0.0, a_s=1.0, s0=0.01, hsm=120)
