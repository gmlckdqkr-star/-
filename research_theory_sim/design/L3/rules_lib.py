"""Candidate rule families for lane L3 (design-time only). All strictly causal: column t uses data <= t."""
import numpy as np


def _prep(close, rf):
    c = np.array(close, dtype=np.float64)
    P, T = c.shape
    # forward-fill NaN closes
    for t in range(1, T):
        bad = ~np.isfinite(c[:, t]); c[bad, t] = c[bad, t - 1]
    lr = np.zeros((P, T))
    with np.errstate(divide='ignore', invalid='ignore'):
        lr[:, 1:] = np.log(c[:, 1:] / c[:, :-1])
    lr[~np.isfinite(lr)] = 0.0
    f = np.where(np.isfinite(rf), rf, 0.0)
    return lr, f


def fam_kelly(close, rf, a, b, H, Hv, v0=0.03):
    """A: L = (a + b*m)/v ; m = EWMA excess log drift (annual), v = EWMA variance (annual)."""
    lr, f = _prep(close, rf); P, T = lr.shape
    am = 1 - 0.5 ** (1 / H); av = 1 - 0.5 ** (1 / Hv)
    m = np.zeros(P); v = np.full(P, v0 / 252); out = np.empty((P, T))
    for t in range(T):
        x = lr[:, t]
        m += am * ((x - f[:, t]) - m); v += av * (x * x - v)
        out[:, t] = (a + b * m * 252) / (v * 252)
    out[:, :20] = np.nan
    return np.clip(out, 0, 3)


def fam_cusum(close, rf, W, Lmax, Hv, mu0=0.0, Lmin=0.0, v0=0.03):
    """B: bounded cumulative sum of standardised excess returns in [-W, W] (Wonham-type clamped log-odds);
    level is linear in the position inside the band: Lmin at -W, Lmax at +W."""
    lr, f = _prep(close, rf); P, T = lr.shape
    av = 1 - 0.5 ** (1 / Hv)
    v = np.full(P, v0 / 252); l = np.zeros(P); out = np.empty((P, T))
    for t in range(T):
        x = lr[:, t]
        z = (x - f[:, t]) / np.sqrt(v) - mu0
        l = np.clip(l + z, -W, W)
        v += av * (x * x - v)
        out[:, t] = Lmin + (Lmax - Lmin) * (l + W) / (2 * W)
    out[:, :20] = np.nan
    return out


def fam_dd(close, rf, N, th, Lhi, Llo, Hv, v0=0.03):
    """C: drawdown from N-day high in units of annual vol: in (Lhi) if dd > -th, else Llo."""
    lr, f = _prep(close, rf); P, T = lr.shape
    av = 1 - 0.5 ** (1 / Hv)
    from scipy.ndimage import maximum_filter1d          # design-time only (causal window [t-N+1, t])
    cl = np.cumsum(lr, axis=1)
    HI = maximum_filter1d(cl, N, axis=1, origin=(N - 1) // 2, mode='nearest')
    v = np.full(P, v0 / 252); out = np.empty((P, T))
    for t in range(T):
        x = lr[:, t]; v += av * (x * x - v)
        dd = (cl[:, t] - HI[:, t]) / np.sqrt(v * 252)
        out[:, t] = np.where(dd > -th, Lhi, Llo)
    out[:, :20] = np.nan
    return out


def fam_vt(close, rf, tau, H, Hv, Llo=0.0, v0=0.03):
    """D: vol target tau/sigma when the H-EWMA excess drift is positive, else Llo."""
    lr, f = _prep(close, rf); P, T = lr.shape
    am = 1 - 0.5 ** (1 / H); av = 1 - 0.5 ** (1 / Hv)
    m = np.zeros(P); v = np.full(P, v0 / 252); out = np.empty((P, T))
    for t in range(T):
        x = lr[:, t]
        m += am * ((x - f[:, t]) - m); v += av * (x * x - v)
        out[:, t] = np.where(m > 0, np.minimum(tau / np.sqrt(v * 252), 3.0), Llo)
    out[:, :20] = np.nan
    return out


def fam_latch(close, rf, N, th, Lup, Ldn, Hv, th_up=None, v0=0.03):
    """E: story latch (Schmitt trigger). z = N-day excess log return / (sigma_daily*sqrt(N)).
    Switch to 'stagnation story' when z < -th, back to 'growth story' when z > +th_up (default th); hold in between.
    Level Lup in growth story, Ldn in stagnation story."""
    lr, f = _prep(close, rf); P, T = lr.shape
    if th_up is None: th_up = th
    av = 1 - 0.5 ** (1 / Hv)
    cx = np.cumsum(lr - f, axis=1)
    v = np.full(P, v0 / 252); st = np.ones(P); out = np.empty((P, T))
    for t in range(T):
        x = lr[:, t]; v += av * (x * x - v)
        if t >= N:
            z = (cx[:, t] - cx[:, t - N]) / np.sqrt(v * N)
            st = np.where(z < -th, 0.0, np.where(z > th_up, 1.0, st))
        out[:, t] = np.where(st > 0, Lup, Ldn)
    out[:, :20] = np.nan
    return out


def fam_kz(close, rf, a, beta, N, kap=1.0, Hv=60, Hz=250, n0=None, mu0=0.02, v0=0.03):
    """G/H: Kelly on the theory's forecast. f = mu_long + beta*z_N (annual arithmetic excess return),
    z_N = N-day excess log return / (long-run daily sigma * sqrt(N)); L = kap * f / sigma_short^2.
    G: mu_long = a (fixed).  H: mu_long = Bayesian-shrunk expanding mean of excess arithmetic return,
    prior mean mu0 with weight n0 years."""
    lr, f = _prep(close, rf); P, T = lr.shape
    av = 1 - 0.5 ** (1 / Hv); az = 1 - 0.5 ** (1 / Hz)
    cx = np.cumsum(lr - f, axis=1)
    v = np.full(P, v0 / 252); vz = v.copy(); out = np.empty((P, T))
    s_ex = np.zeros(P); n = 0
    for t in range(T):
        x = lr[:, t]; v += av * (x * x - v); vz += az * (x * x - vz)
        z = (cx[:, t] - cx[:, max(t - N, 0)]) / np.sqrt(vz * N)
        if n0 is None:
            mu = a
        else:
            s_ex += (x - f[:, t]) + 0.5 * x * x; n += 1
            mu = (n0 * mu0 + s_ex) / (n0 + n / 252.0)
        out[:, t] = kap * (mu + beta * z) / (v * 252)
    out[:, :20] = np.nan
    return np.clip(out, 0, 3)
