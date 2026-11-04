"""M1 multiple-testing statistics on the discovery monthly loss-differential matrix D (N rules x T months, float32):
Hansen (2005) SPA (consistent / lower / upper), studentized, stationary bootstrap (Politis-Romano), mean block 3 months,
B = 1000, seed 20261104; Romano-Wolf (2005) studentized max-t stepdown at 5%; DSR (Bailey & Lopez de Prado 2014);
effective N by greedy leader correlation clustering (rho >= 0.7 primary; 0.5, 0.9 sensitivity) and Li-Ji eigenvalue count."""
import numpy as np
from scipy.stats import norm
SEED = 20261104
B = 1000
MEANBLOCK = 3.0
EULER = 0.5772156649


def stationary_counts(T, B=B, mean_block=MEANBLOCK, seed=SEED):
    rng = np.random.default_rng(seed); p = 1.0 / mean_block
    W = np.zeros((B, T), np.float32)
    for b in range(B):
        idx = np.empty(T, np.int64); t = int(rng.integers(T))
        for i in range(T):
            if i > 0:
                t = int(rng.integers(T)) if rng.random() < p else (t + 1) % T
            idx[i] = t
        W[b] = np.bincount(idx, minlength=T)
    return W


def spa_rw(D, chunk=20000, topM=600, alpha=0.05, verbose=True):
    N, T = D.shape
    W = stationary_counts(T)
    dbar = D.mean(1).astype(np.float64)
    s1 = np.zeros(N); s2 = np.zeros(N)
    for i in range(0, N, chunk):           # pass 1: bootstrap SD of sqrt(T) * mean
        Mb = (W @ D[i:i + chunk].T).astype(np.float64) / T      # (B, n)
        s1[i:i + chunk] = Mb.sum(0); s2[i:i + chunk] = (Mb ** 2).sum(0)
    var = s2 / B - (s1 / B) ** 2
    om = np.sqrt(np.maximum(var, 0) * T)
    good = om > 1e-10
    om_s = np.where(good, om, np.inf)
    tstat = np.sqrt(T) * dbar / om_s
    A = -(om / np.sqrt(T)) * np.sqrt(2 * np.log(np.log(T)))
    gc = np.where(dbar >= A, dbar, 0.0); gl = np.maximum(dbar, 0.0); gu = dbar
    Tspa = max(0.0, float(np.max(tstat[good]))) if good.any() else 0.0
    Tc = np.zeros(B); Tl = np.zeros(B); Tu = np.zeros(B)
    topv = np.full((B, topM), -np.inf); topk = np.full((B, topM), -1, np.int64)
    for i in range(0, N, chunk):           # pass 2
        Mb = (W @ D[i:i + chunk].T).astype(np.float64) / T
        sc = np.sqrt(T) / om_s[i:i + chunk]
        Tc = np.maximum(Tc, ((Mb - gc[i:i + chunk]) * sc).max(1))
        Tl = np.maximum(Tl, ((Mb - gl[i:i + chunk]) * sc).max(1))
        Zc = (Mb - dbar[i:i + chunk]) * sc            # centered studentized (RW, = upper SPA)
        Tu = np.maximum(Tu, Zc.max(1))
        n = Zc.shape[1]; m = min(topM, n)
        part = np.argpartition(-Zc, m - 1, axis=1)[:, :m]
        v = np.take_along_axis(Zc, part, 1)
        allv = np.concatenate([topv, v], 1); allk = np.concatenate([topk, part + i], 1)
        o = np.argsort(-allv, 1)[:, :topM]
        topv = np.take_along_axis(allv, o, 1); topk = np.take_along_axis(allk, o, 1)
        if verbose:
            print('  spa chunk', i, flush=True)
    Tc = np.maximum(Tc, 0); Tl = np.maximum(Tl, 0); Tu = np.maximum(Tu, 0)
    res = dict(T=T, N=N, Tspa=Tspa, p_c=float(np.mean(Tc >= Tspa)), p_l=float(np.mean(Tl >= Tspa)), p_u=float(np.mean(Tu >= Tspa)),
               maxnull_q50=float(np.median(Tu)), maxnull_q95=float(np.quantile(Tu, 0.95)))
    # Romano-Wolf stepdown
    rej = np.zeros(N, bool); crit = []
    order = np.argsort(-np.where(good, tstat, -np.inf))
    while True:
        R = set(np.flatnonzero(rej).tolist())
        mx = np.empty(B)
        for b in range(B):
            vals = topv[b]; ks = topk[b]; j = 0
            while j < topM and ks[j] in R:
                j += 1
            if j == topM:
                raise RuntimeError('RW: more rejections than topM')
            mx[b] = vals[j]
        c = float(np.quantile(mx, 1 - alpha)); crit.append(c)
        new = (~rej) & good & (tstat > c)
        if not new.any():
            break
        rej |= new
    res.update(rw_n=int(rej.sum()), rw_crit=crit)
    return res, dict(dbar=dbar, om=om, tstat=tstat, rw_rej=rej, good=good)


def dsr(x, sr_var, N):
    """x: monthly differential series of the selected rule (active months); sr_var: cross-sectional variance of the
    monthly Sharpe ratios of all trials; N: number of trials. Returns (DSR, SR, SR0)."""
    x = np.asarray(x, float); T = len(x)
    sr = x.mean() / x.std(ddof=1)
    g3 = float(((x - x.mean()) ** 3).mean() / x.std() ** 3); g4 = float(((x - x.mean()) ** 4).mean() / x.std() ** 4)
    N = max(N, 2)
    sr0 = np.sqrt(sr_var) * ((1 - EULER) * norm.ppf(1 - 1.0 / N) + EULER * norm.ppf(1 - 1.0 / (N * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr * sr, 1e-12))
    return float(norm.cdf(z)), float(sr), float(sr0)


def standardize(D):
    Z = D - D.mean(1, keepdims=True)
    sd = np.sqrt((Z.astype(np.float64) ** 2).sum(1, keepdims=True))
    return (Z / np.where(sd > 0, sd, 1)).astype(np.float32), sd[:, 0] > 0


def leader_clusters(D, order, rho=0.7, chunk=4096, cap=60000):
    """greedy leader clustering in the given order (best first). A rule joins the first-found leader with corr >= rho.
    Returns number of leaders (clusters) and leader index list. cap: stop (return None) if leaders exceed cap."""
    Z, ok = standardize(D[order])
    L = np.zeros((0, Z.shape[1]), np.float32); nlead = 0
    for i in range(0, len(order), chunk):
        z = Z[i:i + chunk]; okc = ok[i:i + chunk]
        if nlead:
            mx = (z @ L[:nlead].T).max(1)
            cand = np.flatnonzero((mx < rho) & okc)
        else:
            cand = np.flatnonzero(okc)
        if len(cand):
            zc = z[cand]; C = zc @ zc.T
            newl = []
            assigned = np.zeros(len(cand), bool)
            for j in range(len(cand)):
                if assigned[j]:
                    continue
                newl.append(j)
                assigned |= C[j] >= rho
            add = zc[newl]
            if nlead + len(add) > L.shape[0]:
                L2 = np.zeros((max(2 * L.shape[0], nlead + len(add) + 1024), Z.shape[1]), np.float32); L2[:nlead] = L[:nlead]; L = L2
            L[nlead:nlead + len(add)] = add; nlead += len(add)
            if nlead > cap:
                return None
    return nlead


def lij_meff(D, chunk=20000):
    """Li & Ji (2005) effective number of tests from the eigenvalues of the N x N correlation matrix, computed through
    the T x T Gram matrix of standardized rows (same non-zero eigenvalues)."""
    N, T = D.shape
    G = np.zeros((T, T)); n_ok = 0
    for i in range(0, N, chunk):
        Z, ok = standardize(D[i:i + chunk]); Z = Z[ok].astype(np.float64); n_ok += ok.sum()
        G += Z.T @ Z
    lam = np.linalg.eigvalsh(G)          # eigenvalues of corr matrix (rows standardized to unit norm -> corr = Z Z^T)
    lam = np.clip(lam, 0, None)
    meff = float(np.sum((lam >= 1).astype(float) + (lam - np.floor(lam))))
    return meff, int(n_ok), lam
