"""Causality test and activity counts of every states configuration on the <= 2014 calendar. No performance figure."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
cfgs = json.load(open('/home/user/-/research_xv1/cand/states.configs.json'))
assert len(set(e['name'] for e in cfgs)) == len(cfgs)
X = xv1.frame(xv1.OLD_END)
for e in cfgs:
    c = xv1.Config(**e); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v); r = xv1.ref(v); i0 = len(X) - v.T
    nd = int((o['B'] != r['B']).sum()); eps_B = int((np.diff(np.r_[0, (o['B'] != r['B']).astype(int)]) == 1).sum())
    W = np.asarray(o['Wt']) if 'Wt' in o else np.zeros((v.T, 1))
    nz = int((W != 0).any(axis=1).sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum())
    eps = int((np.diff(np.r_[0, (W != 0).any(axis=1).astype(int)]) == 1).sum())
    act = np.flatnonzero((o['B'] != r['B']) | (W != 0).any(axis=1))
    span = (str(X.index[i0 + act[0]].date()), str(X.index[i0 + act[-1]].date())) if len(act) else (None, None)
    pre = 0
    if e['t0'] is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(e['t0']))) - i0
        pre = int((W[:max(first, 0)] != 0).sum()) + int((o['B'][:max(first, 0)] != r['B'][:max(first, 0)]).sum())
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25)
    print(e['name'], 'rows_B_differs', nd, 'B_episodes', eps_B, 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'first_last_active', span,
          'mode', o.get('mode', 0), 'inc', o.get('inc', 0), 't0', e['t0'], 'active_before_t0', pre, p['result'], p, flush=True)
