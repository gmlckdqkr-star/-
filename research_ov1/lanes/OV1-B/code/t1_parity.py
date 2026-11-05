"""OV1-B step 1: engine parity (no open data used). mode 0 with a random ON and mode 1 with ON = 0 must equal std.engine (v1)
to 1e-12 on all 5 MS1 bases (per-path cagr and equity curves)."""
import os, sys, json, time
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ov1lib as L, std
import eng_ov1b as G
OUT = '/mnt/project-files/research/ov1/lanes/OV1-B/results/'
t0 = time.time(); res = {}
for bn, c in std.contexts().items():
    B, bfn, bp, fs = std.s085(c)
    f_ref, E_ref = std.engine(c, B, bfn, bp, fs)
    rng = np.random.default_rng(1); ONr = rng.normal(0, 0.01, c.r.shape)
    f0, E0, _ = G.engine_s(c, B, bfn, bp, fs, ONr, mode=0)
    f1, E1, o1 = G.engine_s(c, B, bfn, bp, fs, np.zeros(c.r.shape), mode=1)
    rel = lambda a, b: float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-12)))
    res[bn] = dict(P=int(c.P), mode0_cagr_maxabs=float(np.max(np.abs(f0 - f_ref))), mode0_E_maxrel=rel(E0, E_ref),
                   mode1_on0_cagr_maxabs=float(np.max(np.abs(f1 - f_ref))), mode1_on0_E_maxrel=rel(E1, E_ref),
                   mode1_on0_postponed_fills_per_path=float(np.mean(o1[:, 11])), v1_cagr_median=float(np.median(f_ref)))
    print(bn, res[bn], '%.0fs' % (time.time() - t0), flush=True)
ok = all(v['mode0_cagr_maxabs'] <= 1e-12 and v['mode0_E_maxrel'] <= 1e-12 and v['mode1_on0_cagr_maxabs'] <= 1e-12
         and v['mode1_on0_E_maxrel'] <= 1e-12 for v in res.values())
res['PARITY_OK_1e-12'] = bool(ok)
os.makedirs(OUT, exist_ok=True); json.dump(res, open(OUT + 'parity.json', 'w'), indent=1)
print('PARITY_OK', ok)
