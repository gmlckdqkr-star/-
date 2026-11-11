import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
cfgs = json.load(open('/home/user/-/research_xv1/cand/states.configs.json'))
X = xv1.frame(xv1.OLD_END)
for e in cfgs:
    c = xv1.Config(**e); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v); r = xv1.ref(v)
    nd = int((o['B'] != r['B']).sum()); eps_B = int((np.diff(np.r_[0, (o['B'] != r['B']).astype(int)]) == 1).sum())
    W = np.asarray(o['Wt']) if 'Wt' in o else np.zeros((v.T, 1))
    nz = int((W != 0).any(axis=1).sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum())
    eps = int((np.diff(np.r_[0, (W != 0).any(axis=1).astype(int)]) == 1).sum())
    pre = 0
    if e['t0'] is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(e['t0']))) - (len(X) - v.T)
        pre = int((W[:max(first, 0)] != 0).sum()) + int((o['B'][:max(first, 0)] != r['B'][:max(first, 0)]).sum())
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25)
    print(e['name'], 'rows_B_differs', nd, 'B_episodes', eps_B, 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'active_before_t0', pre, p['result'], p, flush=True)
