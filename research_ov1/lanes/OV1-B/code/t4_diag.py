"""OV1-B post-hoc diagnostics (NOT pre-registered, report-only, not selectable, cannot change the verdict):
(a) same run with on_t = 0 for 1999 (the pre-gate window) -> unseen-only contribution; (b) count of decreases kept at the close by
the tax-block rule (k % 252 == 251) on real_ndx_86_14."""
import os, sys, json
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ov1lib as L, std
import eng_ov1b as G, onleg as O
OUT = '/mnt/project-files/research/ov1/lanes/OV1-B/results/'
cal = L.dates()['real_ndx_86_14']
on, info = O.on_series(cal, xcheck=True)
on_u = on.copy(); on_u[on_u.index < pd.Timestamp('2000-01-01')] = 0.0
res = {}
for bn in ('real_ndx_86_14', 'dev250_path', 'dev250_glued'):
    c = std.contexts()[bn]; B, bfn, bp, fs = std.s085(c)
    fr, _ = std.engine(c, B, bfn, bp, fs)
    f, E, o = G.engine_s(c, B, bfn, bp, fs, O.on_ctx(on_u, L.dates()[bn], c.ii), mode=1)
    d = f - fr
    res[bn] = dict(cagr_med=float(np.median(f)), d_med=float(np.median(d)), pw=float(np.mean(d > 1e-5)))
    print('unseen-only on (1999 zeroed)', bn, res[bn], flush=True)
c = std.contexts()['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c)
_, _, ev = G.engine_log(c, B, bfn, bp, fs, np.zeros(c.r.shape), mode=0)
ev = pd.DataFrame(ev, columns=['t', 'dexp', 'kind', 'elig'])
res['real_ndx_v1_decreases'] = dict(level=int((ev.kind == 1).sum()), tax=int((ev.kind == 2).sum()), kept_at_close_k251=int((ev.elig == 0).sum()))
print(res['real_ndx_v1_decreases'])
json.dump(res, open(OUT + 'diag_posthoc.json', 'w'), indent=1)
