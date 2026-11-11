"""Causality test and activity counts of every bridge configuration on the <= 2014 calendar. No performance figure."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
cfgs = json.load(open('/home/user/-/research_xv1/cand/bridge.configs.json'))
assert len(set(e['name'] for e in cfgs)) == len(cfgs), 'configuration names are not unique'
npass = 0
for e in cfgs:
    c = xv1.Config(**e); X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v)
    i0 = len(X) - v.T; r = xv1.ref(v); W = np.asarray(o['Wt']); on = (W != 0).any(axis=1)
    nz = int(on.sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum()); eps = int((np.diff(np.r_[0, on.astype(int)]) == 1).sum())
    act = np.flatnonzero(on); first_a = str(X.index[i0 + act[0]].date()) if len(act) else None; last_a = str(X.index[i0 + act[-1]].date()) if len(act) else None
    t0 = e['t0']
    if t0 is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(t0))) - i0
        pre = int((W[:max(first, 0)] != 0).sum())
    else: pre = 0
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25); npass += int(p['result'] == 'PASS')
    print(e['name'], 'rows_B_differs', int((o['B'] != r['B']).sum()), 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'weight_in_warmup', int(on[:xv1.WARM].sum()),
          'weight_before_t0', pre, 'first_active', first_a, 'last_active', last_a, 'max_weight_sum', round(float(W.sum(axis=1).max()), 6), 'mode', o['mode'], 'inc', o['inc'], p, flush=True)
print('configurations', len(cfgs), 'PASS', npass, 'ALL PASS' if npass == len(cfgs) else 'NOT ALL PASS')
