"""Parity: hyeng (dynamic engine) with constant targets must equal I_INTEGRATE ii.run (el._comb)."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hyeng as H, ii
out = {}
for bn in ['real_ndx_86_14', 'real_spx_55_85', 'dev250_path']:
    for a0, w in [(1.0, {}), (0.0, {'VALPROF4_L1': 1.0}), (0.5, {'VALPROF4_L1': 0.5}), (0.4, {'VALPROF4_L1': 0.3, 'BOND10_L3': 0.3})]:
        t = time.time()
        f1, E1 = ii.run(bn, a0, w)
        names = list(w.keys()); Wv = np.array([w[n] for n in names])
        f2, E2, NT = H.run(bn, a0, Wv, names)
        T = E1.shape[1]
        c1 = np.median(H.cagr(f1, T)); c2 = np.median(H.cagr(f2, T))
        md = float(np.max(np.abs(np.log(np.maximum(f1, 1e-12)) - np.log(np.maximum(f2, 1e-12)))))
        key = '%s|%.1f|%s' % (bn, a0, ','.join('%s=%.2f' % kv for kv in w.items()))
        out[key] = dict(ii=float(c1), hy=float(c2), maxlogdiff=md)
        print(key, round(c1, 5), round(c2, 5), 'maxlogdiff %.2e' % md, 'ntr/yr %.1f' % (np.median(NT) / (T / 252)), round(time.time() - t, 1), flush=True)
json.dump(out, open('/mnt/project-files/research/hybrid/results/parity_le2014.json', 'w'), indent=1)
