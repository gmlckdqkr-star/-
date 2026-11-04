"""candidate rule families (causal, numpy). close: (P,T) index level; rf: (P,T) daily simple rate."""
import numpy as np

def _ema(x, span):
    a = 2.0 / (span + 1); out = np.empty_like(x); s = x[:, 0].copy()
    for t in range(x.shape[1]):
        xt = x[:, t]; s = np.where(np.isfinite(s), s + a * (xt - s), xt); s = np.where(np.isfinite(xt), s, s)
        out[:, t] = s
    return out

_memo = {}
def prep(close, rf, sv=20):
    key = (id(close), sv)
    if key in _memo: return _memo[key]
    lp = np.log(close)
    lr = np.zeros_like(lp); lr[:, 1:] = np.diff(lp, axis=1); lr = np.nan_to_num(lr)
    v = _ema(lr ** 2, sv); v[:, :5] = np.nan
    sig2 = np.maximum(252 * v, 0.03 ** 2)
    d = dict(lp=lp, lr=lr, sig2=sig2, rfa=rf * 252, ema={})
    _memo.clear(); _memo[key] = d
    return d

def ema_lp(d, n):
    if n not in d['ema']: d['ema'][n] = _ema(d['lp'], n)
    return d['ema'][n]

def F_kelly(close, rf, p):
    """L = kf*(mu_hat - rf)/sig2, mu_hat = m0 + A*(lp-EMA_ns) - B*(lp-EMA_nl)."""
    d = prep(close, rf, p.get('sv', 20))
    mu = np.full_like(d['lp'], p['m0'])
    if p.get('A', 0): mu = mu + p['A'] * (d['lp'] - ema_lp(d, p['ns']))
    if p.get('B', 0): mu = mu - p['B'] * (d['lp'] - ema_lp(d, p['nl']))
    L = p.get('kf', 0.5) * (mu - d['rfa']) / d['sig2']
    return np.clip(L, 0, 3)

def F_filter(close, rf, p):
    """vol-target Kelly base, switched off when log price is below its EMA_ns (minus a band of bnd*sigma*sqrt(ns/252))."""
    d = prep(close, rf, p.get('sv', 20))
    L = p.get('kf', 0.5) * (p['m0'] - d['rfa']) / d['sig2']
    g = d['lp'] - ema_lp(d, p['ns'])
    band = p.get('bnd', 0.0) * np.sqrt(d['sig2'] * p['ns'] / 252)
    on = g > -band
    if p.get('B', 0):
        L = L - p.get('kf', 0.5) * p['B'] * (d['lp'] - ema_lp(d, p['nl'])) / d['sig2']
    return np.clip(np.where(on, L, 0.0), 0, 3)

def F_kelly_gap(close, rf, p):
    """F_kelly plus ratchet-gap term: mu += G*log(Mhat/sig), Mhat = running max of sig decaying with half-life mhl."""
    d = prep(close, rf, p.get('sv', 20))
    sig = np.sqrt(d['sig2'])
    key = ('M', p['mhl'])
    if key not in d['ema']:
        dec = np.exp(-np.log(2) / p['mhl']); M = np.empty_like(sig); m = np.nan_to_num(sig[:, 0], nan=0.0)
        for t in range(sig.shape[1]):
            s = np.nan_to_num(sig[:, t], nan=0.0); m = np.maximum(s, m * dec); M[:, t] = m
        d['ema'][key] = M
    gap = np.log(np.maximum(d['ema'][key], 1e-6) / sig)
    mu = p['m0'] + p['A'] * (d['lp'] - ema_lp(d, p['ns'])) - p['B'] * (d['lp'] - ema_lp(d, p['nl'])) + p['G'] * gap
    L = p.get('kf', 0.5) * (mu - d['rfa']) / d['sig2']
    return np.clip(L, 0, 3)
