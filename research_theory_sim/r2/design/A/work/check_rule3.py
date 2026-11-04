from grid import *
import rule
for mech in (True, False):
    v = []
    for sd in SEEDS:
        w = get(sd, mech); B = rule.target_levels(close_of(w['r']), w['rf']); v.append(evaluate(B, w)['cagr_med'])
    print('rule.py on seeds 2,3 mech', mech, '%.4f' % np.mean(v))
