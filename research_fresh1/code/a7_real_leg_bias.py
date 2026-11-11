"""FRESH1 A7 (information only, not pre-registered): how often would a method with a TRUE long-run growth X clear the
"beat v1's real 1986-2014 number (31.08%)" leg, if its 30-year outcomes are spread like v1's own simulated outcomes?
Dispersion model = v1's 500 dev250_path outcomes shifted so that the median equals X. <=2014 only."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
C = std.contexts(); c = C['dev250_path']; B, bfn, bp, fs = std.s085(c); f, E = std.engine(c, B, bfn, bp, fs)
cr = C['real_ndx_86_14']; Br, bfr, bpr, fsr = std.s085(cr); real = float(std.engine(cr, Br, bfr, bpr, fsr)[0][0])
med = float(np.median(f)); lf = np.log1p(f)
out = dict(v1_path_median=med, v1_real=real, model='log-growth shift of v1 path outcomes', rows={})
for X in (0.16, 0.18, 0.20, 0.25, 0.30, 0.35, 0.40):
    sh = np.log1p(X) - np.log1p(med)
    out['rows']['true_%d' % round(X * 100)] = dict(p_beat_real_31=float(np.mean(lf + sh > np.log1p(real))), p_beat_path_median_16=float(np.mean(lf + sh > np.log1p(med))))
json.dump(out, open('/mnt/project-files/research/fresh1/results/a7_real_leg_bias.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
