import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(2000, 1)
tg = 's10'
for a in (0.5, 1.0):
    evaluate(W, tg, trk=0.35, f=1.032, p=0.0, kon=False, a_s=a, s0=0.01, hsm=120)
evaluate(W, tg, trk=0.35, f=1.239, p=0.0, kon=False, a_s=0.5, s0=0.01, hsm=120)
evaluate(W, tg, trk=0.35, f=1.032, p=0.0, kon=False, a_s=0.5, s0=0.01, hsm=120, sexp=2520)
evaluate(W, tg, trk=0.35, f=1.032, p=0.0, kon=False, a_s=0.5, s0=0.01, hsm=250)
evaluate(W, tg, trk=0.35, const=1.5)
