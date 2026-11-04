"""Exploration 3: turbulence rules. Form A: L = clip(beta*(vf/vs - c0), 0, 3). Seeds 1-2 (P=500 each)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F
W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
G = {m: F.logret(W[m]['close']) for m in W}
VS = {m: F.ewma(G[m][0] ** 2, 250, G[m][1], F.V0) for m in W}
for hf in (10, 25):
    VF = {m: F.ewma(G[m][0] ** 2, hf, G[m][1], F.V0) for m in W}
    for c0 in (0.6, 0.9):
        for beta in (1.5, 3.0):
            out = []
            for m in W:
                B = np.clip(beta * (VF[m] / VS[m] - c0), 0, 3)
                out.append(H.evaluate('turbA hf=%d c0=%.1f b=%.1f' % (hf, c0, beta), B, W[m], BASE[m], 'ON' if m else 'OFF'))
            for row in out: print(H.fmt(row))
