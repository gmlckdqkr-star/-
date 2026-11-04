import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
from grid import *
W = worlds(1000, 3)
print('BASE', W[True]['base'], W[False]['base'], flush=True)
for mech in (True, False):
    w = W[mech]
    for Lc in (0.5, 1.0, 1.5, 2.0):
        for th in (0.1, 0.25, 0.5):
            B = rules.track(np.full(w['r'].shape, Lc), w['close'], w['rf'], theta=th)
            s = ee.summary(ee.run(w['r'], w['rf'], B))
            print('mech', mech, 'track const', Lc, 'theta', th, 'med %.4f lev %.2f tr %.2f' % (s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']), flush=True)
