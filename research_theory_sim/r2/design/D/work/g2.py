import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(600, 1)
for p in (1.0, 1.5, 2.0):
    for hv in (60, 120, 250):
        for f in (0.75, 1.0, 1.25, 1.5):
            if hv == 60 and p in (1.0, 2.0) and f in (1.0, 1.5): continue
            evaluate(W, 's2', f=f, hv=hv, p=p)
