import sys, json, time
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, cross
cfgs = json.load(open('/home/user/-/research_xv1/cand/cross.configs.json'))
only = sys.argv[1:]
for e in cfgs:
    if only and e['name'] not in only: continue
    t_ = time.time(); c = xv1.Config(**e); X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v)
    r = xv1.ref(v); nb = int((o['B'] != r['B']).sum())
    W = np.asarray(o['Wt']) if 'Wt' in o else np.zeros((v.T, 1))
    nz = int((W != 0).any(axis=1).sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum())
    eps = int((np.diff(np.r_[0, (W != 0).any(axis=1).astype(int)]) == 1).sum())
    pre = 0
    if e['t0'] is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(e['t0']))) - (len(X) - v.T)
        pre = int((W[:max(first, 0)] != 0).sum()) + int((o['B'][:max(first, 0)] != r['B'][:max(first, 0)]).sum())
    extra = ''
    if e['func'] == 'sbc_cap' and e['name'] == 'SBC_P1':   # structure check of the rebuilt v1 base level (no performance)
        off = r['B'] == 0; cau = np.asarray(v.c.F['shock6m'][0], dtype=bool); pre_ = cross._base_pre(v)
        rb = np.where(off, 0.0, np.where(cau, np.minimum(pre_, 1.0), pre_)); extra = 'rebuild_mismatch_vs_v1 %d' % int((rb != r['B']).sum())
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25)
    print(e['name'], '|', e['family'], '| rows_B_differs', nb, 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'weight_or_B_before_t0', pre, 't0', e['t0'], extra, p, '%.0fs' % (time.time() - t_), flush=True)
