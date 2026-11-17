"""FRESH1 audit A2b: how much of v1's real 1986-2014 result comes from the macro alarms that were designed on that same path.
Also: share of v1 simulated paths reaching 30%/yr, and (added after the independent verifier's review, 2026-11-11) an
always-on trend exit that uses no alarm information. <=2014 only.
Fix 2026-11-11: share_lt_hold1x is now paired (same path); the first version compared with the pool-median 1x hold."""
import sys, json, copy, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
ov = std.ov
C = std.contexts(); out = {}
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'dev250_path', 'dev250_glued'):
    c = C[bn]
    B, bfn, bp, fs = std.s085(c); f1, E1 = std.engine(c, B, bfn, bp, fs)
    c2 = copy.copy(c); c2.F = {k: np.zeros_like(v) for k, v in c.F.items()}; c2._c = dict(c._c)      # all alarms off
    B2, bfn, bp, fs = std.s085(c2); f2, E2 = std.engine(c2, B2, bfn, bp, fs)
    # always-on trend exit: below the 200-day mean (2% band) -> cash, whatever the alarms say; no caution tier; brake sees no alarms
    B3 = np.where(ov.trend_gate(c, 200, 0.02, None), 0.0, B2); f3, E3 = std.engine(c2, B3, bfn, bp, fs)
    hf, _ = std.hold(c, 1)
    out[bn] = dict(v1=float(np.median(f1)), v1_alarms_off=float(np.median(f2)), trend_exit_always_on=float(np.median(f3)),
                   hold1x=float(np.median(hf)), alarm_share_pp=float(np.median(f1) - np.median(f2)),
                   alarm_info_vs_always_on_exit_pp=float(np.median(f1) - np.median(f3)), days_changed=float(np.mean(B != B2)))
    if len(f1) > 1:
        out[bn].update(share_ge_30=float(np.mean(f1 >= 0.30)), share_ge_25=float(np.mean(f1 >= 0.25)),
                       share_lt_hold1x_same_path=float(np.mean(f1 < hf)), share_lt_median_hold1x=float(np.mean(f1 < np.median(hf))),
                       paired_d_vs_always_on_exit=float(np.median(f1 - f3)), win_share_vs_always_on_exit=float(np.mean(f1 - f3 > 1e-5)))
json.dump(out, open('/mnt/project-files/research/fresh1/results/a2b_alarm_share.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
