"""FRESH1 audit A2: where does v1's real 1986-2014 outcome sit inside v1's own simulated distributions?
<=2014 data only (MS1 contexts). Also sibling tracking errors for A1 calibration."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import bk, rx, ce
C = std.contexts()
out = {}
E = {}
for bn, c in C.items():
    B, bfn, bp, fs = std.s085(c)
    fin, EE = std.engine(c, B, bfn, bp, fs)
    E[bn] = EE
    out[bn] = dict(n=int(len(fin)), median=float(np.median(fin)), mean=float(np.mean(fin)),
                   pct={str(q): float(np.percentile(fin, q)) for q in (5, 10, 25, 50, 75, 90, 95, 99)} if len(fin) > 1 else None,
                   years=EE.shape[1] / 252)
    out[bn]['_fin'] = fin
real = out['real_ndx_86_14']['median']
for bn in ('dev250_path', 'dev250_glued'):
    f = out[bn]['_fin']
    out[bn]['share_paths_ge_real'] = float(np.mean(f >= real))
    out[bn]['real_percentile'] = float(np.mean(f < real) * 100)
# real path is 29 yrs, simulated 30: compare on CAGR (annualised) so horizon is comparable.
# sibling tracking error on the real path (daily log-return difference, annualised)
c = C['real_ndx_86_14']
sib = {
 'AV23_brake1.0': (bk.C3sig(c), ce.alt, ce.AV23, 0.1),
 'C3_nobrake': (bk.C3sig(c), std.ident, np.zeros(1), 0.1),
 'hold3x': (np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5),
 'hold1x_engine': (np.full(c.r.shape, 1.0), std.ident, np.zeros(1), 0.5),
}
lv = np.diff(np.log(E['real_ndx_86_14'][0]))
out['v1_real_vol'] = float(lv.std() * np.sqrt(252))
out['siblings_real'] = {}
for nm, m in sib.items():
    fin, EE = std.engine(c, *m)
    ls = np.diff(np.log(EE[0])); d = ls - lv
    out['siblings_real'][nm] = dict(cagr=float(fin[0]), te=float(d.std() * np.sqrt(252)), corr=float(np.corrcoef(ls, lv)[0, 1]),
                                    dlog_per_yr=float(d.mean() * 252))
# same siblings in the simulated world: median d, share of single paths won
cp = C['dev250_path']
B, bfn, bp, fs = std.s085(cp); fr, _ = std.engine(cp, B, bfn, bp, fs)
out['siblings_path'] = {}
for nm, mk in {'AV23_brake1.0': lambda c: (bk.C3sig(c), ce.alt, ce.AV23, 0.1), 'C3_nobrake': lambda c: (bk.C3sig(c), std.ident, np.zeros(1), 0.1)}.items():
    fc, _ = std.engine(cp, *mk(cp)); d = fc - fr
    out['siblings_path'][nm] = dict(median_d=float(np.median(d)), win_share=float(np.mean(d > 1e-5)), sd_d=float(d.std()))
for bn in list(out):
    if isinstance(out[bn], dict) and '_fin' in out[bn]: del out[bn]['_fin']
json.dump(out, open('/mnt/project-files/research/fresh1/results/a2_incumbent.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
