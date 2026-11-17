"""Reviewer: crafted synthetic path that forces a position to outlive its episode (a new episode opens while the old sleeve
is still held) and compares bridge.py with the independent version. Synthetic numbers only; counts printed."""
import sys, json, types
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand'); sys.path.insert(0, '/home/user/-/research_xv1/cand/tests')
import numpy as np, xv1, bridge
import rev_bridge_xcheck as rx
cfgs = [e for e in json.load(open('/home/user/-/research_xv1/cand/bridge.configs.json')) if e['func'] in ('staged_bridge', 'hold_to_top')]
for pairs in (60, 100):
    sem = np.r_[np.full(100, 0.001), np.full(30, -0.02), np.tile([0.12, 1 / 1.12 - 1], pairs), np.full(25, 0.03), np.full(35, -0.02), np.full(900, 0.0002)]
    T = len(sem); sv, sB = rx.synth(1, T); sv.x['semis'] = sem
    for k in ('ret:SOXL', 'ret:USD'): sv.x[k] = np.full(T, np.nan)
    sB = np.zeros(T); sv.ref_target = np.zeros(T)
    xv1.ref = lambda vv, _b=sB: dict(B=_b.copy(), bfn=None, bp=np.zeros(1), fstep=0.5)
    rx.ST.clear()
    for e in cfgs:
        W = np.asarray(getattr(bridge, e['func'])(sv, **e['params'])['Wt']); M = rx.mine(e, sv, sB)
        print('pairs', pairs, e['name'], 'differing rows', int((np.abs(W - M) > 1e-12).any(axis=1).sum()), 'weight levels in thirds of the budget', sorted(set(np.round(W[:, 0] / (e['params'].get('budget', 0.2) / 3), 6).tolist())),
              'rows with weight', int((W != 0).sum()), 'weight changes', int((np.diff(W[:, 0]) != 0).sum()))
    print('   corner counters', dict(sorted(rx.ST.items())))
