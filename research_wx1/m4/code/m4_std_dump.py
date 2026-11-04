"""Dump MS1 base data (NDX/SPX/rf from the same loader std.contexts uses, cut at 2014-12-31) and s0.85 pre-tax and
after-tax daily equity on the real bases. <=2014 only."""
import os, sys, json, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
os.environ['NUMBA_CACHE_DIR'] = S + 'nb'
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import jp, ov
R, M = jp.calendar('1928-01-03', '2014-12-31')
assert R.index.max() <= pd.Timestamp('2014-12-31')
out = pd.DataFrame({'NDX': R['NDX'], 'SPX': R['SPX'], 'rf': M['rf'], 'y10': M['y10'], 'y3m': M['y3m'], 'cs': M['cs']}, index=R.index)
out.to_pickle(S + 'data/ms1_base.pkl')
C = std.contexts()
res = {}
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'):
    c = C[bn]
    rB, rbf, rbp, rfs = std.s085(c)
    cg, EE = std.engine(c, rB, rbf, rbp, rfs)
    cg0, EE0 = std.engine(c, rB, rbf, rbp, rfs, tax=0.0)
    X = c.X if hasattr(c, 'X') else None
    print(bn, 'cagr', cg, 'pretax cagr', cg0, 'EE shape', EE.shape, 'ii', c.ii.shape, 'r', c.r.shape, flush=True)
    res[bn] = dict(cagr=float(cg[0]), cagr_pretax=float(cg0[0]), n=int(EE.shape[1]))
    np.save(S + 'data/s085_EE_%s.npy' % bn, EE[0]); np.save(S + 'data/s085_EE0_%s.npy' % bn, EE0[0])
    np.save(S + 'data/ii_%s.npy' % bn, c.ii[0])
    np.save(S + 'data/B_%s.npy' % bn, np.asarray(rB)[0])
json.dump(res, open(S + 'data/s085_real.json', 'w'), indent=1)
print('done')
