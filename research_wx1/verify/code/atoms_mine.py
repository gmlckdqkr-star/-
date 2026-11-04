import numpy as np, pandas as pd, json
W1 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/cache/'
AM = json.load(open(W1+'atoms_meta.json')); rules = np.load(W1+'rules.npy')
z = np.load(W1+'prim.npz'); pm = json.load(open(W1+'prim_meta.json'))
dall = pd.to_datetime(z['dates'].astype('datetime64[D]'))
def my_atom(prim, tr, q, dirn):
    x = z[prim].astype(float); kind = pm[prim]['kind']
    b = np.log(np.where(x > 0, x, np.nan)) if kind == 'pos' else x
    s = pd.Series(b)
    if tr == 'L': y = s
    elif tr[0] == 'Z': n = int(tr[1:]); y = (s - s.rolling(n).mean())/s.rolling(n).std()
    elif tr[0] == 'C': n = int(tr[1:]); y = s - s.shift(n)
    elif tr[0] == 'S': n = int(tr[1:]); y = s - s.rolling(n).mean()
    y = y.values
    # expanding quantile of every 5th finite past value, after 504 finite values, threshold uses values strictly before t
    out = np.full(len(y), -1, np.int8); samp = []; seen = 0
    for t in range(len(y)):
        if seen >= 504 and len(samp) > 10 and np.isfinite(y[t]):
            th = np.quantile(np.array(samp), q)      # linear interpolation, same as (m-1)*q
            out[t] = int(y[t] > th) if dirn == '>' else int(y[t] <= th)
        if np.isfinite(y[t]):
            if seen % 5 == 0: samp.append(y[t])
            seen += 1
    return out
for e, a0 in (('ndx', '1985-01-02'), ('spx', '1954-01-04')):
    A = np.load(W1+'atoms_%s.npy' % e, mmap_mode='r'); dts = pd.to_datetime(np.load(W1+'dates_%s.npy' % e).astype('datetime64[D]'))
    i0 = dall.get_indexer(dts)
    for rid in (1744, 130752, 126171, 6914):
        k = int(rules[rid][0]); m = AM[k]
        mine = my_atom(m['prim'], m['tr'], m['q'], m['dir'])[i0]
        w = np.asarray(A[k]); agree = (mine == w).mean()
        print(e, rid, m, 'agree %.6f' % agree, 'n_true', int((w == 1).sum()), 'n_unknown', int((w < 0).sum()))
