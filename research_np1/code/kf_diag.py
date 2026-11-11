"""NP1-KF added diagnostic (NOT pre-registered, labelled as such): how much of KF20A / KF60A's <=2014 gain comes from 2009.
real NDX: overlay restricted to 2009 only / everything except 2009. dev250_path: paired d split by whether the path has any active day
whose SOURCE date is in 2009."""
import os, sys, json
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
LANE = '/mnt/project-files/research/np1/'
sys.path.insert(0, LANE + 'code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, kf
C = std.contexts(); D = L.dates(); Cs = kf.level_series(); out = {}
for bn in ('real_ndx_86_14', 'dev250_path'):
    c = C[bn]; B = L.v1_B(c); bfn, bp, fs = L.v1_parts(c)
    Cl = L.path_series(Cs, bn) if bn == 'dev250_path' else L.gather(Cs, bn)
    y09 = np.asarray(D[bn].year)[c.ii] == 2009
    fr, _ = std.engine(c, B, bfn, bp, fs)
    for v in ('KF20A', 'KF60A'):
        on, _ = kf.on_window(Cl, v); act = on & (B == 1.0)
        f_all, _ = std.engine(c, kf.overlay(B, on, v), bfn, bp, fs)
        f_09, _ = std.engine(c, kf.overlay(B, on & y09, v), bfn, bp, fs)
        f_x09, _ = std.engine(c, kf.overlay(B, on & ~y09, v), bfn, bp, fs)
        r = dict(d_all_mean=float(np.mean(f_all - fr)), d_only2009_mean=float(np.mean(f_09 - fr)), d_excl2009_mean=float(np.mean(f_x09 - fr)),
                 d_excl2009_med=float(np.median(f_x09 - fr)), cagr_excl2009_med=float(np.median(f_x09)), v1_med=float(np.median(fr)),
                 active_days_2009=int((act & y09).sum()), active_days_other=int((act & ~y09).sum()))
        if bn == 'dev250_path':
            has = (act & y09).any(1); d = f_all - fr
            r.update(paths_with_2009_active=int(has.sum()), d_mean_paths_with_2009=float(d[has].mean()) if has.any() else None,
                     d_mean_paths_without_2009=float(d[~has].mean()), win_without_2009_changed=float(np.mean(d[~has & (np.abs(d) > 1e-5)] > 0)))
        out['%s|%s' % (v, bn)] = r; print(v, bn, json.dumps({k: (round(x, 5) if isinstance(x, float) else x) for k, x in r.items()}), flush=True)
json.dump(out, open(LANE + 'results/kf_diag_2009.json', 'w'), indent=1)
