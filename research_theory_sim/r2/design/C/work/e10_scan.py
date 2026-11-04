"""Exploration 10: scan around the two-signal Kelly. Params: c, a, b, hf (fast var hl), hs (slow hl), hss (very slow hl),
hm (mid hl for lvr). L = clip((c + a*log(v_hs/v_hss) + b*log(v_hm/v_hs)) / (252*v_hf), 0, 3). Seeds 1-2, P=500 each."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F
W = {m: H.world([1, 2], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
GG = {m: F.logret(W[m]['close']) for m in W}
cache = {}
def V(m, hl):
    if (m, hl) not in cache: cache[(m, hl)] = F.ewma(GG[m][0] ** 2, hl, GG[m][1], F.V0)
    return cache[(m, hl)]
def run(c, a, b, hf=20, hs=250, hss=1000, hm=60, tag=''):
    out = []
    for m in W:
        L = (c + a * np.log(V(m, hs) / V(m, hss)) + b * np.log(V(m, hm) / V(m, hs))) / (252 * V(m, hf))
        out.append(H.evaluate('scan c=%.3f a=%.2f b=%.2f hf=%d hs=%d hss=%d hm=%d' % (c, a, b, hf, hs, hss, hm),
                              np.clip(L, 0, 3), W[m], BASE[m], 'ON' if m else 'OFF'))
    print(H.fmt(out[0])[:150]); print(H.fmt(out[1])[:150])
for a in (0.3, 0.4): run(0.02, a, 0.04)
for hf in (10, 40): run(0.02, 0.2, 0.04, hf=hf)
for hs, hss in ((125, 750), (250, 1500), (500, 1500)): run(0.02, 0.2, 0.04, hs=hs, hss=hss)
for hm in (20, 120): run(0.02, 0.2, 0.04, hm=hm)
