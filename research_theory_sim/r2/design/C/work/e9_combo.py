"""Exploration 9 (extension of 8): two-signal Kelly. m_hat = c + a*lvs + b*lvr60, lvs = log(vs250/vs1000), lvr60 = log(vf60/vs250);
L = clip(m_hat / (252*vf20), 0, 3). Seeds 1-2 (P=500 each). Small grid."""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F
W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
FE = {}
for m in W:
    g, ok = F.logret(W[m]['close'])
    vs = F.ewma(g ** 2, 250, ok, F.V0); vss = F.ewma(g ** 2, 1000, ok, F.V0)
    FE[m] = dict(lvs=np.log(vs / vss), lvr60=np.log(F.ewma(g ** 2, 60, ok, F.V0) / vs), vf=F.ewma(g ** 2, 20, ok, F.V0))
for c, a, b in itertools.product((0.02, 0.03), (0.1, 0.15, 0.2), (0.04, 0.08)):
    out = []
    for m in W:
        f = FE[m]
        B = np.clip((c + a * f['lvs'] + b * f['lvr60']) / (252 * f['vf']), 0, 3)
        out.append(H.evaluate('combo c=%.2f a=%.2f b=%.2f' % (c, a, b), B, W[m], BASE[m], 'ON' if m else 'OFF'))
    print(H.fmt(out[0])); print(H.fmt(out[1]))
