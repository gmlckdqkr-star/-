import numpy as np, pandas as pd, sys
sys.argv = ['x']
from eng_mine import sim, R, M, W1, rules     # reuses verifier engine (re-runs the small check above on import)
dts = pd.to_datetime(np.load(W1+'dates_ndx.npy').astype('datetime64[D]'))
A = np.asarray(np.load(W1+'atoms_ndx.npy', mmap_mode='r'))
pos = R.index.get_indexer(dts); r = R['NDX'].fillna(0.0).values[pos]; rf = M['rf'].values[pos]
print('last date', dts[-1])
for rid in (237118, 1744, 214645, 29783):
    dec, g = sim(A, r, rf, rules[rid])
    gs = pd.Series(g, index=dts)
    print(rid, 'conf 2000-14 adv vs 1x %.4f' % (gs.loc['2000-01-03':'2014-12-31'].mean()*252), 'disc ndx %.4f' % (gs.loc['1986-01-02':'1999-12-31'].mean()*252))
