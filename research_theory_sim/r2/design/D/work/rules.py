"""candidate rule family (design only; pure numpy, causal). Final rule goes to rule.py."""
import numpy as np


def ewma_loop(x, hl, init):
    lam = 0.5 ** (1.0 / hl)
    P, T = x.shape
    out = np.empty((P, T)); s = np.full(P, init, dtype=float) if np.ndim(init) == 0 else init.astype(float).copy()
    for t in range(T):
        s = lam * s + (1 - lam) * x[:, t]
        out[:, t] = s
    return out


def kfun(R):
    """annual excess (over rf) earned per unit of level by the 3x product + cash mix, beyond the index excess."""
    return R / 3 - 0.0245 / 3 - 0.282 * np.maximum(R - 0.02, 0)


def prep(close, rf, y10=None):
    c = np.asarray(close, dtype=float)
    prev = np.concatenate([np.full((c.shape[0], 1), np.nan), c[:, :-1]], axis=1)
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    lr = np.where(ok, np.log(np.where(ok, c, 1.0) / np.where(ok, prev, 1.0)), 0.0)
    act = (ok & (lr != 0)).astype(float)
    R = np.where(np.isfinite(rf), rf, 0.0) * 252
    return lr, act, R


def target(close, rf, y10=None, f=1.0, hv=40, p=2.0, Lmax=3.0, mu0=0.035, n0=None, a_s=0.0, s0=0.01, hs=None,
           q=0.0, hx=500, a_r=0.0, wr=250, est='sq', sfloor=0.08, sref=0.17, cache=None, hsm=None, kon=True, sexp=None):
    lr, act, R = prep(close, rf, y10)
    P, T = lr.shape
    key = ('v', hv, est)
    if cache is not None and key in cache: v = cache[key]
    else:
        if est == 'sq': v = ewma_loop(lr ** 2 * 252, hv, sref ** 2)
        else: v = (ewma_loop(np.abs(lr) * np.sqrt(252), hv, sref * np.sqrt(2 / np.pi)) * np.sqrt(np.pi / 2)) ** 2
        if cache is not None: cache[key] = v
    sig = np.sqrt(np.maximum(v, sfloor ** 2))
    mu = np.full((P, T), mu0)
    if n0 is not None:                                    # online premium: shrink expanding mean toward mu0
        ex = np.where(act > 0, lr - np.where(np.isfinite(rf), rf, 0.0), 0.0)
        cs = np.cumsum(ex, axis=1) * 252; nd = np.cumsum(act, axis=1)
        N = nd / 252.0
        mu = (n0 * mu0 + N * np.where(nd > 0, cs / np.maximum(nd, 1), 0.0) + 0.5 * N * sig ** 2 * 0) / (n0 + N)
    if a_s != 0.0 and y10 is not None:                    # funding-carry tilt (term spread)
        S = np.where(np.isfinite(y10), y10 / 100.0 - R, np.nan)
        if hsm is not None:
            S = np.where(np.isfinite(S), ewma_loop(np.where(np.isfinite(S), S, s0), hsm, s0), np.nan)
        if sexp is not None:
            Sf = np.where(np.isfinite(S), S, 0.0); nS = np.cumsum(np.isfinite(S), axis=1)
            base = (sexp * s0 + np.cumsum(Sf, axis=1)) / (sexp + nS)
        elif hs is None: base = s0
        else:
            Sf = np.where(np.isfinite(S), S, s0)
            base = ewma_loop(Sf, hs, s0)
        mu = mu + a_s * np.where(np.isfinite(S), np.clip(S - base, -0.03, 0.03), 0.0)
    if a_r != 0.0:                                        # robust rate-trend tilt: clipped daily changes summed over wr days
        dR = np.zeros_like(R); dR[:, 1:] = np.diff(R, axis=1)
        dR = np.clip(dR, -0.0075, 0.0075)
        cs = np.cumsum(dR, axis=1); tr = cs - np.concatenate([np.zeros((P, wr)), cs[:, :-wr]], axis=1)
        mu = mu - a_r * np.clip(tr, -0.03, 0.03)
    L = f * (mu + (kfun(R) if kon else 0.0)) / (sig ** p * sref ** (2 - p))
    if q != 0.0:                                          # capital-ledger tilt: decayed sum of past excess log returns
        ex = lr - np.where(np.isfinite(rf), rf, 0.0)
        xh = ewma_loop(ex, hx, 0.0) * (hx / np.log(2))
        L = L * np.exp(-q * np.clip(xh, -1.5, 1.5))
    L = np.clip(L, 0.0, Lmax)
    ea = ewma_loop(act, 20, 0.0)
    L = np.where(ea > 0.5, L, 0.0)
    return L


def track(D, close, rf, theta=0.25, warm=300, delay=2):
    """exposure tracking: choose the requested level so that the EFFECTIVE exposure of the 3x/cash mix (which drifts
    while the level is unchanged) stays close to the desired exposure D. Replicates the engine's level/step logic."""
    c = np.asarray(close, dtype=float)
    P, T = c.shape
    prev = np.concatenate([np.full((P, 1), np.nan), c[:, :-1]], axis=1)
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    r = np.where(ok, np.where(ok, c, 1.0) / np.where(ok, prev, 1.0) - 1.0, 0.0)
    f = np.where(np.isfinite(rf), rf, 0.0)
    g3 = 1 + 3 * r - 2 * f - 0.0245 / 252
    gc = 1 + np.maximum(f - 0.02 / 252, 0.0) * (1 - 0.154)
    lev = np.arange(0, 3.01, 0.5)
    held = np.zeros(P); u = np.zeros(P); cur = np.zeros(P)
    q = np.zeros((P, delay))
    B = np.zeros((P, T))
    Dn = np.where(np.isfinite(D), np.clip(D, 0, 3), 0.0)
    for t in range(T):
        if t >= warm:
            want = q[:, 0].copy(); q[:, :-1] = q[:, 1:]
            if t > warm:
                a = u * g3[:, t]; b = (1 - u) * gc[:, t]
                u = np.where(a + b > 0, a / np.maximum(a + b, 1e-300), 0.0)
            m = (want != cur) | (t == warm)
            u = np.where(m, want / 3, u); cur = np.where(m, want, cur)
        # exposure if we keep the held level: pending level if a change is pending, else drifted effective exposure
        pend = (q[:, -1] != cur) if t >= warm else np.zeros(P, bool)
        Ek = np.where(t >= warm, np.where(pend, q[:, -1], 3 * u), held)
        d = Dn[:, t]
        cost_keep = np.abs(Ek - d)
        # best level that is a valid change from held
        dist = np.abs(lev[None, :] - d[:, None]) + (theta if t >= warm else 0.0)
        valid = (np.abs(lev[None, :] - held[:, None]) >= 0.5) | ((lev[None, :] == 0) & (held[:, None] > 0))
        dist = np.where(valid, dist, np.inf)
        j = np.argmin(dist, axis=1); bc = dist[np.arange(P), j]
        ch = bc < cost_keep
        held = np.where(ch, lev[j], held)
        B[:, t] = held
        if t == warm - 1: q[:, :] = held[:, None]
        elif t >= warm: q[:, -1] = held
    return B
