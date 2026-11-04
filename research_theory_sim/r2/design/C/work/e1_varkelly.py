"""Exploration 1: variance-timed Kelly  L = clip(c / (252*v_f), 0, 3), grid over c and half-life. Seeds 1-2 (P=500 each)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F

W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
for m in W: print('mech', m, {k: round(v, 4) if isinstance(v, float) else v for k, v in BASE[m].items()})
G = {m: F.logret(W[m]['close']) for m in W}
for hl in (10, 30, 100):
    VF = {m: F.ewma(G[m][0] ** 2, hl, G[m][1], F.V0) for m in W}
    for c in (0.02, 0.04, 0.06):
        for m in W:
            B = np.clip(c / (252 * VF[m]), 0, 3)
            row = H.evaluate('varkelly hl=%d c=%.2f' % (hl, c), B, W[m], BASE[m], 'ON' if m else 'OFF')
            print(H.fmt(row))
