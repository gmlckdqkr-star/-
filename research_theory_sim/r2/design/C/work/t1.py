import sys, time; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/C')
import numpy as np, sim
T = 7860
for mech in (True, False):
    t0 = time.time(); s = sim.simulate(500, T, 1, mechanism=mech); print('t=%.1f' % (time.time()-t0))
    sim.describe(s, str(mech))
