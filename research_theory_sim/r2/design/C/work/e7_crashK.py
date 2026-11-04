"""Exploration 7: crash-scar Kelly. m_hat = c + a*C, C = EWMA(hl) of crash indicator (g < -z*sd_slow) per year;
L = clip(m_hat / (252*vf20), 0, 3). Seeds 1-2 (P=500 each)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F
W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
G = {m: F.logret(W[m]['close']) for m in W}
VS = {m: F.ewma(G[m][0] ** 2, 250, G[m][1], F.V0) for m in W}
VF = {m: F.ewma(G[m][0] ** 2, 20, G[m][1], F.V0) for m in W}
z = 2.5
CI = {m: F.ewma((G[m][0] < -z * np.sqrt(VS[m])).astype(float), 250, G[m][1], 0.0) * 252 for m in W}
for m in W: print('C pct', m, np.percentile(CI[m][:, 300:], [10, 25, 50, 75, 90]).round(2))
for c in (-0.01, 0.0, 0.01):
    for a in (0.005, 0.01, 0.02):
        out = []
        for m in W:
            B = np.clip((c + a * CI[m]) / (252 * VF[m]), 0, 3)
            out.append(H.evaluate('crashK hl250 z2.5 c=%.3f a=%.3f' % (c, a), B, W[m], BASE[m], 'ON' if m else 'OFF'))
        for row in out: print(H.fmt(row))
