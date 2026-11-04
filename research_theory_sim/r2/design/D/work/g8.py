import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(2000, 1)
tg = 's8'
for c in (1.25, 1.75):
    evaluate(W, tg, trk=0.25, const=c)
for f in (1.0, 1.25, 1.5):
    evaluate(W, tg, trk=0.25, f=f, p=0.0)
for p, f in ((1.0, 1.0), (1.0, 1.25), (0.5, 1.25)):
    evaluate(W, tg, trk=0.25, f=f, p=p, hv=500)
for a in (1.0, 2.0):
    evaluate(W, tg, trk=0.25, f=1.25, p=0.0, a_s=a, s0=0.01)
for q in (1.0, 2.0):
    evaluate(W, tg, trk=0.25, f=1.25, p=0.0, q=q, hx=500)
