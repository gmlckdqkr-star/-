"""s085_weak harness (thread 's0.85 지수보다 못한 해 원인 고치기', 2026-11-04). <=2014 only.
Diagnosis of years where s0.85 lags the 1x index, on MS1 contexts."""
import sys, os, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
sys.path.insert(0, '/mnt/project-files/research/c3_bear/code'); import bd
import beng, ce, bk, jp, ov
WARM = beng.WARM

def run(c, B, bfn, bp, fstep, **kw):
    k = dict(beng.F1); k['fstep'] = fstep; k.update(kw); pp, D = beng._args(k)
    return bd.runPR(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64),
                    np.ascontiguousarray(bk.features(c)), int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'],
                    pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']))

def real_dates():
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX')
    i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
    nd = X.index[i0:][WARM:]
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X2 = jp.mkX(R, M, 'SPX')
    out = {'real_ndx_86_14': nd}
    for nm, a in (('real_spx_55_85', '1955-01-03'), ('real_spx_70_85', '1970-01-02')):
        j0 = X2.index.searchsorted(pd.Timestamp(a)) - ov.WARM; out[nm] = X2.index[j0:][WARM:]
    return out
