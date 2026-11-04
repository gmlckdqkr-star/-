"""diagnostics on fresh seeds (no selection): (a) where the edge comes from; (b) 250-day block-resampled paths."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import sim, rule, exec_engine as ee
np.seterr(all='ignore')
T = 7860
out = {}
# (a) edge vs mechanism strength, seed 10000 ON
s = sim.simulate(2000, T, seed=10000, mechanism=True, return_state=True)
r, rf, p = s['r'], s['rf'], s['params']
B = rule.target_levels(np.cumprod(1 + r, 1), rf)
rr = ee.run(r, rf, B)['cagr']; c5 = ee.run(r, rf, np.full(r.shape, 0.5))['cagr']; h1 = ee.hold(r, rf, 1)['cagr']
edge = rr - c5
lev = s['state']['lev'][:, 300:].mean(1)
for k in ('Phi', 'beta', 'phi_v', 'kappa', 'c', 'tau_L', 'b_X', 'sigma_u', 'sigma_f', 'Rbar', 'g0'):
    print('corr(edge vs const0.5, %-7s) = %+.3f' % (k, np.corrcoef(edge, p[k])[0, 1]))
print('corr(edge, time-avg speculator leverage) = %+.3f' % np.corrcoef(edge, lev)[0, 1])
foot = p['Phi'] * lev
q = np.quantile(foot, [0, 0.25, 0.5, 0.75, 1.0])
rows = []
for i in range(4):
    m = (foot >= q[i]) & (foot <= q[i + 1])
    rows.append(dict(quartile=i + 1, rule=float(np.median(rr[m])), const05=float(np.median(c5[m])), hold1x=float(np.median(h1[m]))))
    print('footprint quartile', i + 1, {k: round(v, 4) for k, v in rows[-1].items()})
out['edge_by_effective_footprint_quartile'] = rows
# (b) block-resampled synthetic paths (mimics the real headline construction)
Pl, Tl = 300, 300 + 100 * 252
sl = sim.simulate(Pl, Tl, seed=10010, mechanism=True)
g = np.random.default_rng(10011)
nb = int(np.ceil(T / 250)); K = 8
Rb = np.empty((Pl * K, nb * 250)); Fb = np.empty_like(Rb)
for i in range(Pl):
    for k in range(K):
        st = g.integers(0, Tl - 250, nb)
        idx = (st[:, None] + np.arange(250)[None, :]).ravel()
        Rb[i * K + k] = sl['r'][i, idx]; Fb[i * K + k] = sl['rf'][i, idx]
Rb = Rb[:, :T]; Fb = Fb[:, :T]; Rb[:, 0] = 0
Bb = rule.target_levels(np.cumprod(1 + Rb, 1), Fb)
res = dict(rule=ee.summary(ee.run(Rb, Fb, Bb))['cagr_med'], hold1x=ee.summary(ee.hold(Rb, Fb, 1))['cagr_med'],
           hold2x=ee.summary(ee.hold(Rb, Fb, 2))['cagr_med'], hold3x=ee.summary(ee.hold(Rb, Fb, 3))['cagr_med'])
for L in (0.5, 1.0, 1.5): res[f'const{L}'] = ee.summary(ee.run(Rb, Fb, np.full(Rb.shape, L)))['cagr_med']
# same long paths, contiguous 30y windows (no block joins) for comparison
Rc = sl['r'][:, :T].copy(); Fc = sl['rf'][:, :T]; Rc[:, 0] = 0
res['contiguous_rule'] = ee.summary(ee.run(Rc, Fc, rule.target_levels(np.cumprod(1 + Rc, 1), Fc)))['cagr_med']
res['contiguous_hold1x'] = ee.summary(ee.hold(Rc, Fc, 1))['cagr_med']
print('block-resampled (250d) ON:', {k: round(v, 4) for k, v in res.items()})
out['block250_on'] = res
json.dump(out, open('/mnt/project-files/research/theory_sim/design/L1/work/diag_final.json', 'w'), indent=1)
