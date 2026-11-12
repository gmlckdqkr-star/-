"""FRESH1 audit A6b (information only): path vs glued medians of v1 by source era. Shows where the glued-over-path premium comes from.
Eras: NDX 1986-99, NDX 2000-14, NDX 1986-2014 (MS1), S&P 1955-85, S&P 1928-54. <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import jp, ov
out = {}
def run(nm, stream, cal_a, a, b):
    R, M = jp.calendar(cal_a, b); X = jp.mkX(R, M, stream); F = ov.flags_hist(X)
    j0 = max(X.index.searchsorted(pd.Timestamp(a)) - ov.WARM, 0)
    Xe = X.iloc[j0:]; Fe = F.iloc[j0:]
    ii = ov.boot_idx(len(Xe), P=500, years=30, block=250, seed=7, lo=1)
    cg = ov.Ctx(Xe, Fe, ii); cp = ov.Ctx(Xe, Fe, ii); cp.F = std.path_flags(Xe, ii); cp._c = {}
    o = {}
    for k, c in (('glued', cg), ('path', cp)):
        B, bfn, bp, fs = std.s085(c); f, E = std.engine(c, B, bfn, bp, fs)
        o[k] = float(np.median(f)); o[k + '_hold1x'] = std.row(*std.hold(c, 1))[0]['cagr']
        o[k + '_alarm_days'] = float(np.mean((c.F['inv'] | c.F['shock6m'])[:, ov.WARM:]))
    o['glued_minus_path'] = o['glued'] - o['path']; out[nm] = o
    print(nm, {k: round(v, 4) for k, v in o.items()}, flush=True)
run('ndx_1986_99', 'NDX', '1984-01-03', '1986-01-02', '1999-12-31')
run('ndx_2000_14', 'NDX', '1984-01-03', '2000-01-03', '2014-12-31')
run('ndx_1986_14', 'NDX', '1984-01-03', '1986-01-02', '2014-12-31')
run('spx_1955_85', 'SPX', '1928-01-03', '1955-01-03', '1985-12-31')
run('spx_1930_54', 'SPX', '1928-01-03', '1930-01-02', '1954-12-31')
json.dump(out, open('/mnt/project-files/research/fresh1/results/a6b_era_pools.json', 'w'), indent=1)
