"""FRESH1 audit A6 (AMEND_A2): locate v1's real S&P 1955-85 outcome inside path/glued distributions built from that era only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import jp, ov
R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX'); F = ov.flags_hist(X)
out = {}
C = std.contexts()
for nm, a in (('spx_55_85', '1955-01-03'), ('spx_70_85', '1970-01-02')):
    j0 = X.index.searchsorted(pd.Timestamp(a)) - ov.WARM
    Xe = X.iloc[j0:]; Fe = F.iloc[j0:]
    ii = ov.boot_idx(len(Xe), P=500, years=30, block=250, seed=7, lo=1)
    cg = ov.Ctx(Xe, Fe, ii)
    cpth = ov.Ctx(Xe, Fe, ii); cpth.F = std.path_flags(Xe, ii); cpth._c = {}
    creal = C['real_' + nm]; B, bfn, bp, fs = std.s085(creal); fr, _ = std.engine(creal, B, bfn, bp, fs); real = float(fr[0])
    o = dict(real_v1=real, real_hold1x=std.row(*std.hold(creal, 1))[0]['cagr'])
    for k, c in (('glued', cg), ('path', cpth)):
        B, bfn, bp, fs = std.s085(c); f, E = std.engine(c, B, bfn, bp, fs)
        o[k] = dict(median=float(np.median(f)), p25=float(np.percentile(f, 25)), p75=float(np.percentile(f, 75)), p10=float(np.percentile(f, 10)),
                    p90=float(np.percentile(f, 90)), real_percentile=float(np.mean(f < real) * 100), hold1x=std.row(*std.hold(c, 1))[0]['cagr'])
    out[nm] = o
json.dump(out, open('/mnt/project-files/research/fresh1/results/a6_yardstick.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
