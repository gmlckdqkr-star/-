"""causal feature helpers used in design (numpy only)."""
import numpy as np

def ewma(x, span, axis=1, init=None):
    a = 2.0 / (span + 1)
    out = np.empty_like(x)
    s = x[:, 0].copy() if init is None else np.full(x.shape[0], init, dtype=float)
    for t in range(x.shape[1]):
        s = s + a * (x[:, t] - s)
        out[:, t] = s
    return out

def feats(r, rf, vol_span=20, mem_hl=252, ema_span=200):
    lr = np.log1p(r)
    v = ewma(lr ** 2, vol_span, init=0.0001)
    sig = np.sqrt(252 * v)
    d = np.exp(-np.log(2) / mem_hl)
    M = np.empty_like(sig); m = sig[:, 0].copy()
    for t in range(sig.shape[1]):
        m = np.maximum(sig[:, t], m * d); M[:, t] = m
    lp = np.cumsum(lr, axis=1)
    pk = np.maximum.accumulate(lp, axis=1)
    dd = lp - pk
    ema = ewma(lp, ema_span)
    return dict(lr=lr, sig=sig, M=M, gap=M / sig, dd=dd, tr=lp - ema, lp=lp)

def fwd_sum(x, h):
    c = np.cumsum(x, axis=1)
    out = np.full_like(x, np.nan)
    out[:, :-h] = c[:, h:] - c[:, :-h]
    return out
