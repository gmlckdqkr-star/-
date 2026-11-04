import sys
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A/work')
import numpy as np, sim, rule
from clock import clock_rule
from harness import close_of
w = sim.simulate(200, 7860, 7, mechanism=True)
cl = close_of(w['r'])
B1 = rule.target_levels(cl, w['rf'])
B2 = clock_rule(cl, p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
d = np.abs(np.nan_to_num(B1, nan=-1) - B2)[:, 1:]
big = d > 1e-9
print('frac cols differing', big.mean(), 'paths with any', big.any(1).sum())
ii, tt = np.where(big)
print('first diffs (path, col, B1, B2):', [(int(a), int(b) + 1, round(float(B1[a, b + 1]), 3), round(float(B2[a, b + 1]), 3)) for a, b in zip(ii[:8], tt[:8])])
print('max col with diff', tt.max() + 1 if tt.size else None, ' diffs with |d|>0.01:', (d > 0.01).sum())
jj = np.where(d > 0.01)
print('cols of |d|>0.01:', np.unique(jj[1] + 1)[:40], '... paths', np.unique(jj[0]))
