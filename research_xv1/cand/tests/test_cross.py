"""Package "cross": for every configuration of cross.configs.json the activity counts on the <= 2014 calendar and the causality
test. Counts only (rows, changes, episodes, dates of the first and last active row); no return or account figure is computed.
Activity counts are on the account rows (the engine ignores target weights on the warm-up rows; those are shown separately)."""
import sys, json, time
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1, cross
cfgs = json.load(open('/home/user/-/research_xv1/cand/cross.configs.json'))
assert len(set(e['name'] for e in cfgs)) == len(cfgs)
only = sys.argv[1:]; WARM = xv1.WARM; n_pass = 0; n_run = 0
for e in cfgs:
    if only and e['name'] not in only: continue
    t_ = time.time(); c = xv1.Config(**e); X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v)
    i0 = len(X) - v.T; r = xv1.ref(v); dB = o['B'] != r['B']; nb = int(dB[WARM:].sum())
    assert o['B'].min() >= 0 and o['B'].max() <= 3
    W = np.asarray(o['Wt'], dtype=float).reshape(v.T, -1) if 'Wt' in o else np.zeros((v.T, 1))
    assert W.min() >= 0 and W.sum(axis=1).max() <= 1 + 1e-12
    on = (W != 0).any(axis=1); Wa = np.r_[np.zeros((1, W.shape[1])), W[WARM:]]           # account rows, starting from no position
    nz = int(on[WARM:].sum()); ch = int((np.diff(Wa, axis=0) != 0).any(axis=1).sum())
    eps = int((np.diff((Wa != 0).any(axis=1).astype(int)) == 1).sum())
    act = np.flatnonzero((on | dB) & (np.arange(v.T) >= WARM))
    span = ('first_active %s last_active %s' % (X.index[i0 + act[0]].date(), X.index[i0 + act[-1]].date())) if len(act) else 'never active'
    pre = 0
    if e['t0'] is not None:
        first = int(np.searchsorted(X.index.values, np.datetime64(e['t0']))) - i0
        assert str(X.index[i0 + first].date()) == e['t0']                                  # T0 is a calendar row
        pre = int(on[WARM:max(first, WARM)].sum()) + int(dB[:max(first, 0)].sum())
    extra = ''
    if e['func'] == 'sbc_cap' and e['name'] == 'SBC_P1':   # structure check of the rebuilt v1 base level (no performance)
        off = r['B'] == 0; cau = np.asarray(v.c.F['shock6m'][0], dtype=bool); pre_ = cross._base_pre(v)
        rb = np.where(off, 0.0, np.where(cau, np.minimum(pre_, 1.0), pre_)); extra = 'rebuild_mismatch_vs_v1 %d' % int((rb != r['B']).sum())
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25); n_run += 1; n_pass += p['result'] == 'PASS'
    print(e['name'], '|', e['family'], '| rows_B_differs', nb, 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps, 'w_rows_in_warmup', int(on[:WARM].sum()),
          span, 'weight_or_B_before_t0', pre, 't0', e['t0'], extra, p, '%.0fs' % (time.time() - t_), flush=True)
print('configurations', n_run, 'PASS', n_pass)
