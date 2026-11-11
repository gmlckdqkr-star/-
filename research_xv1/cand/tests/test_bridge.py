import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
cfgs = json.load(open('/home/user/-/research_xv1/cand/bridge.configs.json'))
for e in cfgs:
    c = xv1.Config(**e); X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v)
    r = xv1.ref(v); W = np.asarray(o['Wt']); nz = int((W != 0).any(axis=1).sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum())
    eps = int((np.diff(np.r_[0, (W != 0).any(axis=1).astype(int)]) == 1).sum())
    t0 = e['t0']
    if t0 is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(t0))) - (len(X) - v.T)
        pre = int((W[:max(first, 0)] != 0).sum())
    else: pre = 0
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25)
    print(e['name'], 'rows_B_differs', int((o['B'] != r['B']).sum()), 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'weight_before_t0', pre, p, flush=True)
