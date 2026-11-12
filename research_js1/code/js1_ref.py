"""Independent numpy reference for one rule (no bit tricks): z per map on a packed obs set, and decode of codes."""
import numpy as np
COST = [0.006, 0.003, 0.003]
def cond(A, code):
    code = int(code); sh = code & 31; a = (code >> 5) & 2047; b = (code >> 16) & 2047; c = (code >> 27) & 2047; d = (code >> 38) & 2047
    A_, B_, C_, D_ = A[a], A[b], A[c], A[d]
    f = {0: A_, 1: A_ & B_, 2: A_ | B_, 3: A_ & B_ & C_, 4: A_ | B_ | C_, 5: A_ & (B_ | C_), 6: B_ & (A_ | C_), 7: C_ & (A_ | B_), 8: A_ | (B_ & C_),
         9: B_ | (A_ & C_), 10: C_ | (A_ & B_), 11: A_ & B_ & C_ & D_, 12: (A_ & B_) | (C_ & D_), 13: A_ & B_ & (C_ | D_), 14: A_ & (B_ | C_ | D_),
         15: A_ | B_ | C_ | D_, 16: (A_ | B_) & (C_ | D_)}
    return f[sh]
def zref(on_obs, obs_c, obs_t, X, m, min_on=30):
    """on_obs bool per obs; obs sorted by (country, year); X (3,NC,NY) raw outcomes. Exposure-neutral pooled z (PRECOMMIT)."""
    x = X[m, obs_c, obs_t]; n = len(x); nOn = on_obs.sum()
    if nOn < min_on or n - nOn < min_on or 2 * nOn < n: return None
    skill = 0.0; var = 0.0; flips = 0
    for c in np.unique(obs_c):
        i = obs_c == c; xi = x[i]; oi = on_obs[i]; ti = obs_t[i]; nu = len(xi); mu = xi.mean(); p = oi.mean()
        skill += float(((xi - mu) * oi).sum()); var += p * (1 - p) * nu / (nu - 1) * float(((xi - mu) ** 2).sum()) if nu > 1 else 0
        flips += int(((oi[1:] != oi[:-1]) & (ti[1:] == ti[:-1] + 1)).sum())
    return (skill - COST[m] * flips) / np.sqrt(var) if var > 0 else 0.0
