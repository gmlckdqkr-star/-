import numpy as np

def logret(close):
    c = np.where(np.isfinite(close) & (close > 0), close, np.nan)
    lc = np.log(c)
    lr = np.diff(lc, axis=1, prepend=lc[:, :1])
    lr = np.where(np.isfinite(lr), lr, 0.0)
    lr[:, 0] = 0.0
    return lr

def ewm(x, hl, init=None):
    a = 1 - np.exp(np.log(0.5) / hl)
    out = np.empty_like(x); v = x[:, 0].copy() if init is None else init.copy()
    for t in range(x.shape[1]):
        v = (1 - a) * v + a * x[:, t]; out[:, t] = v
    return out

def feats(close, hl_fast=10, hl_slow=120, hl_ma=100, prior_vol=0.17):
    lr = logret(close)
    P, T = lr.shape
    v0 = np.full(P, (prior_vol ** 2) / 252)
    vf = ewm(lr ** 2, hl_fast, v0); vs = ewm(lr ** 2, hl_slow, v0)
    lp = np.cumsum(lr, axis=1)
    ma = ewm(lp, hl_ma, lp[:, 0])
    hi = np.maximum.accumulate(lp, axis=1)
    n = np.arange(1, T + 1)
    k = 252.0  # prior weight 1 year
    vlong = (np.cumsum(lr ** 2, axis=1) + k * v0[:, None]) / (n + k)
    return dict(lr=lr, lp=lp, vf=vf, vs=vs, ma=ma, dd=lp - hi, vlong=vlong)
