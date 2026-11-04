"""WS1 A1 runner: index direction oracle map. Output results/a1_index.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsidx as W

CTX = sys.argv[1] if len(sys.argv) > 1 else 'ctx_r.npz'
z = np.load(CTX)
DY = {'dev250_path': 0.015, 'real_ndx_86_14': 0.015, 'real_spx_55_85': 0.05}
PG = [.50, .55, .60, .65, .70, .75, .80, .85, .90, .95, 1.0]
res = {}
t0 = time.time()
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'dev250_path'):
    r = z[bn + '_r'][:, W.WARM:]; rf = z[bn + '_rf'][:, W.WARM:]
    pr = W.products(r, rf, DY[bn])
    h3 = W.hold3(r, rf)
    res[bn] = {'hold3x_med': float(np.median(h3)), 'years': r.shape[1] / 252, 'P': r.shape[0], 'cells': {}}
    nseed = 40 if r.shape[0] == 1 else 4
    for mode, mn in ((0, 'L3_I3'), (1, 'L3_cash')):
        for h in (1, 5, 21):
            row = []
            for p in PG:
                v = np.concatenate([W.run_paths(pr, h, p, 1000 + s, mode) for s in range(nseed)])
                row.append(float(np.median(v)))
            res[bn]['cells']['%s_h%d' % (mn, h)] = row
            print(bn, mn, h, ' '.join('%.3f' % x for x in row), '%.0fs' % (time.time() - t0), flush=True)
res['p_grid'] = PG
json.dump(res, open('/mnt/project-files/research/wide_shape/results/a1_index.json', 'w'), indent=1)
