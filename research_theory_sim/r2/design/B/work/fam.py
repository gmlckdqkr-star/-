"""candidate rule family (design only). Two-clock Kelly:
   level = clip(k * (mu0 + bf*log(s_mid/s_fast) + bl*log(s_mid/s_long) - bh*(m_hope - mu0)) / s_fwd^2, 0, 3)"""
import numpy as np
SQ = 1.25 * np.sqrt(252)
def ewm(a, h, init):
    lam = 1 - 0.5 ** (1 / h); out = np.empty_like(a); s = init.copy()
    for t in range(a.shape[1]):
        s = s + lam * (a[:, t] - s); out[:, t] = s
    return out
def feats(close, rf, hs=(10, 15, 20, 25, 40, 80, 160, 320, 640), hm=(1, 3)):
    lc = np.log(close)
    x = np.diff(lc, axis=1, prepend=lc[:, :1]); x = np.where(np.isfinite(x), x, 0.0)
    a = SQ * np.abs(x)
    F = {'x': x}
    for h in hs: F['s%d' % h] = ewm(a, h, np.full(close.shape[0], 0.17))
    ex = 252 * (x - rf)
    for y in hm: F['m%d' % y] = ewm(ex, 252 * y, np.full(close.shape[0], 0.03 - 0.0145))
    for y in hm: F['y%d' % y] = ewm(252 * x, 252 * y, np.full(close.shape[0], 0.06)) - 252 * rf   # yardstick: today's rf
    # expanding arithmetic excess-return sum and count (for prior-shrunk premium learning)
    exa = np.expm1(x) - rf
    F['cum'] = np.cumsum(exa, axis=1); F['n'] = np.arange(1, close.shape[1] + 1)[None, :] / 252.0
    return F
def level(F, k=0.5, mu0=0.03, hf=20, hmid=80, hl=640, hfwd=40, bf=0.0, bl=0.0, bh=0.0, hy=1, smooth=0, learn=0, tau=0.025):
    s_f, s_m, s_l, s_w = F['s%d' % hf], F['s%d' % hmid], F['s%d' % hl], F['s%d' % hfwd]
    mu = mu0
    if learn:
        n0 = s_l ** 2 / tau ** 2                     # prior weight in years implied by the frozen prior sd tau
        mu = (n0 * mu0 + F['cum']) / (n0 + F['n'])
    e = mu + bf * np.log(s_m / s_f) + bl * np.log(s_m / s_l) - bh * (F[hy if isinstance(hy, str) else 'm%d' % hy] + s_w ** 2 / 2 - mu)
    L = k * e / s_w ** 2
    if smooth: L = ewm(L, smooth, L[:, 0])
    return np.clip(L, 0, 3)
