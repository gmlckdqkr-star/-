"""FRESH1 audit A2b: how much of v1's real 1986-2014 result comes from the macro alarms that were designed on that same path.
Also: share of v1 simulated paths reaching 30%/yr. <=2014 only."""
import sys, json, copy, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import bk
C = std.contexts(); out = {}
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'dev250_path', 'dev250_glued'):
    c = C[bn]
    B, bfn, bp, fs = std.s085(c); f1, E1 = std.engine(c, B, bfn, bp, fs)
    c2 = copy.copy(c); c2.F = {k: np.zeros_like(v) for k, v in c.F.items()}; c2._c = dict(c._c)
    B2, bfn, bp, fs = std.s085(c2); f2, E2 = std.engine(c2, B2, bfn, bp, fs)
    h1 = std.row(*std.hold(c, 1))[0]['cagr']
    out[bn] = dict(v1=float(np.median(f1)), v1_alarms_off=float(np.median(f2)), hold1x=h1, alarm_share_pp=float(np.median(f1) - np.median(f2)),
                   days_changed=float(np.mean(B != B2)))
    if len(f1) > 1:
        out[bn]['share_ge_30'] = float(np.mean(f1 >= 0.30)); out[bn]['share_ge_25'] = float(np.mean(f1 >= 0.25)); out[bn]['share_lt_hold1x'] = float(np.mean(f1 < h1))
json.dump(out, open('/mnt/project-files/research/fresh1/results/a2b_alarm_share.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
