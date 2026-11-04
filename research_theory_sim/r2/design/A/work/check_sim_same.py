import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A/work'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np, sim, sim_frozen_copy as sf
for mech in (True, False):
    a = sim.simulate(100, 2000, 3, mechanism=mech); b = sf.simulate(100, 2000, 3, mechanism=mech)
    print(mech, np.array_equal(a['r'], b['r']), np.array_equal(a['rf'], b['rf']), np.array_equal(a['y10'], b['y10']))
