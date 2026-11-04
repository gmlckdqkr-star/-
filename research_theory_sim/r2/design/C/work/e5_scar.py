"""Exploration 5: scar-Kelly. L = clip((c + a*lvs) / (252*vf), 0, 3), lvs = log(vs250/vs1000). Seeds 1-2 (P=500 each)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F
W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
G = {m: F.logret(W[m]['close']) for m in W}
VS = {m: F.ewma(G[m][0] ** 2, 250, G[m][1], F.V0) for m in W}
VSS = {m: F.ewma(G[m][0] ** 2, 1000, G[m][1], F.V0) for m in W}
LVS = {m: np.log(VS[m] / VSS[m]) for m in W}
for m in W: print('lvs pct', m, np.percentile(LVS[m][:, 300:], [5, 25, 50, 75, 95]).round(2))
for hf in (20, 60):
    VF = {m: F.ewma(G[m][0] ** 2, hf, G[m][1], F.V0) for m in W}
    for c in (0.0, 0.015):
        for a in (0.03, 0.08):
            out = []
            for m in W:
                B = np.clip((c + a * LVS[m]) / (252 * VF[m]), 0, 3)
                out.append(H.evaluate('scarK hf=%d c=%.3f a=%.2f' % (hf, c, a), B, W[m], BASE[m], 'ON' if m else 'OFF'))
            for row in out: print(H.fmt(row))
