import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(600, 1)
print('BASE ON', W[True]['base'], 'OFF', W[False]['base'])
# stage 1: vol-scaled fractional Kelly with funding hurdle (f, hv, p)
for p in (0.0, 1.0, 2.0):
    for hv in (20, 60):
        for f in (0.5, 1.0, 1.5):
            evaluate(W, 's1', f=f, hv=hv, p=p)
