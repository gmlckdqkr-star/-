"""Causality test, level-scale test and activity counts of every agree configuration on the <= 2014 calendar. No performance figure.
Usage: test_agree.py [first [last]]   (0-based positions in agree.configs.json, to run the configurations in several processes)"""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
import t_world; t_world.old()
import agree
cfgs = json.load(open('/home/user/-/research_xv1/cand/agree.configs.json'))
assert len(set(e['name'] for e in cfgs)) == len(cfgs) == 12
assert len(set(xv1.Config(**e).hash for e in cfgs)) == len(cfgs)
NAMES = dict(agree4=agree.NAMES_SEMI, qqq_agree=agree.NAMES_NDX, ladder=agree.NAMES_LADDER)
FAMILY = dict(agree4='AGREE4', qqq_agree='QQQAGREE', ladder='PURELADDER')
for e in cfgs: assert set(e['names']) == set(NAMES[e['func']]) and len(set(e['names'])) == len(e['names']) and e['family'] == FAMILY[e['func']] and e['t0'] is None, e['name']
a = int(sys.argv[1]) if len(sys.argv) > 1 else 0; b = int(sys.argv[2]) if len(sys.argv) > 2 else len(cfgs) - 1
X = xv1.frame(xv1.OLD_END); W0 = xv1.WARM
for e in cfgs[a:b + 1]:
    c = xv1.Config(**e); v = xv1.View(X, xv1.extras(c.names, X.index)); o = c.make(v); r = xv1.ref(v); i0 = len(X) - v.T
    m = xv1._call(c.make, v)                                   # the evaluator's own normaliser (raises on a weight on a missing instrument)
    B = np.asarray(o['B'], dtype=float); W = np.asarray(o['Wt'], dtype=float) if 'Wt' in o else np.zeros((v.T, 1))
    assert B.min() >= 0 and B.max() <= 3 and W.min() >= 0 and W.sum(axis=1).max() <= 1.0 + 1e-12 and not np.isnan(W).any() and not np.isnan(B).any()
    assert 'G' not in o or not np.isnan(np.asarray(o['G'])).any()
    dB = B != r['B']; nzr = (W != 0).any(axis=1); act = dB | nzr
    nd = int(dB.sum()); eps_B = int((np.diff(np.r_[0, dB.astype(int)]) == 1).sum())
    nz = int(nzr.sum()); ch = int((np.diff(W, axis=0) != 0).any(axis=1).sum()); eps = int((np.diff(np.r_[0, nzr.astype(int)]) == 1).sum())
    one = int(((W != 0).sum(axis=1) > 1).sum())                # rows with more than one instrument
    rows = np.flatnonzero(act); acc = rows[rows >= W0]
    span = (str(X.index[i0 + acc[0]].date()), str(X.index[i0 + acc[-1]].date())) if len(acc) else (None, None)
    p = xv1.prefix_test(c.make, c.names, end=xv1.OLD_END, n_rand=25); s = xv1.scale_test(c.make, c.names, end=xv1.OLD_END)
    print(e['name'], e['family'], 'rows_B_differs', nd, 'B_episodes', eps_B, 'rows_w_nonzero', nz, 'w_changes', ch, 'episodes', eps,
          'active_rows_in_warmup', int(act[:W0].sum()), 'rows_two_instruments', one, 'first_last_active_account_row', span,
          'mode', m['mode'], 'inc', m['inc'], 'J', m['G'].shape[1], 't0', e['t0'], 'prefix', p['result'], p, 'scale', s, flush=True)
