"""Exploration 6 (upper-bound check, not a candidate: ~17 coefficients): regression filter for m and v fitted on seed 3,
applied to seeds 1-2 (P=500 each). L = clip(k * m_hat / v_hat, 0, 3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, feat as F, sim
import scipy.ndimage as nd

def features(close):
    g, ok = F.logret(close)
    vs = F.ewma(g ** 2, 250, ok, F.V0); vss = F.ewma(g ** 2, 1000, ok, F.V0)
    fs = []
    for hf in (5, 10, 25, 60): fs.append(np.log(F.ewma(g ** 2, hf, ok, F.V0) / vs))
    sd = np.sqrt(vs); cr = np.maximum(0, -g - 2.5 * sd) / sd; ci = (g < -2.5 * sd).astype(float)
    for hl in (20, 63, 126, 250):
        fs.append(F.ewma(cr, hl, ok, 0.0) * 252); fs.append(F.ewma(ci, hl, ok, 0.0) * 252)
    lc = np.log(close)
    for w in (63, 250):
        mx = nd.maximum_filter1d(lc, size=w, axis=1, origin=(w - 1) // 2)
        mx = np.maximum.accumulate(lc, axis=1) if False else mx
        fs.append((lc - mx) / np.sqrt(vs * 252))
    fs.append(np.log(vs / vss))
    fs.append((lc - np.roll(lc, 63, axis=1)) / np.sqrt(vs * 252))
    return fs, vs

d = sim.simulate(500, H.T, 3, mechanism=True, diag=True)
p = d['params']; EY2 = p['Ybar'] ** 2 * (1 + 1 / p['kY'])
v = d['diag']['var_d'] + d['diag']['lam'] * EY2[:, None]; m = d['diag']['m']
fs, vs = features(100 * np.cumprod(1 + d['r'], axis=1))
sl = slice(400, None)
X = np.column_stack([f[:, sl].ravel() for f in fs] + [np.ones(m[:, sl].size)])
bm, *_ = np.linalg.lstsq(X, m[:, sl].ravel(), rcond=None)
bv, *_ = np.linalg.lstsq(X, np.log(v / vs)[:, sl].ravel(), rcond=None)
W = {mm: H.world([1, 2], 500, mm) for mm in (True, False)}
BASE = {mm: H.baselines(W[mm]) for mm in W}
for mm in W:
    fs, vs = features(W[mm]['close'])
    Xa = np.stack(fs + [np.ones_like(vs)], axis=-1)
    mh = Xa @ bm; vh = np.exp(Xa @ bv) * vs   # v from diag is annual, vs daily: ratio carries the 252
    mh[:, :1000] = 0.0  # note: the maximum_filter is centred (non-causal) in this upper-bound check
    for k in (0.5, 1.0):
        B = np.clip(k * mh / vh, 0, 3)
        print(H.fmt(H.evaluate('regUB k=%.1f' % k, B, W[mm], BASE[mm], 'ON' if mm else 'OFF')))
