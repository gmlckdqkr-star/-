"""WX1-M4 multiple-testing statistics on the discovery matrix (months x N):
Hansen (2005) SPA (consistent / upper / lower p) with the stationary bootstrap (mean block 3 months, 1,000 reps, seed 7),
Romano-Wolf studentized step-down at 5 %, Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) with N total and two
effective N (eigen participation ratio; leader clustering at rho >= 0.9). Same SPA/RW on the s0.85-relative matrix
(secondary). Top-20 by discovery mean (vs 1x) = confirmation list.  Out: results/stats.json"""
import json, sys, numpy as np
from scipy.stats import norm, skew, kurtosis
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
B, MB, SEED, ALPHA = 1000, 3.0, 7, 0.05


def sb_counts(T, B, mb, seed):
    rng = np.random.default_rng(seed); p = 1.0 / mb
    C = np.zeros((B, T), np.float32)
    for b in range(B):
        i = rng.integers(T); idx = np.empty(T, np.int64)
        for t in range(T):
            if t > 0:
                i = rng.integers(T) if rng.random() < p else (i + 1) % T
            idx[t] = i
        C[b] = np.bincount(idx, minlength=T)
    return C


def spa_rw(D, C):
    T, N = D.shape
    m = D.mean(axis=0).astype(np.float64)
    Mb = (C @ D).astype(np.float64) / T                      # B x N bootstrap means
    om = np.sqrt(T * Mb.var(axis=0)); om = np.where(om > 0, om, np.inf)
    t = np.sqrt(T) * m / om
    Tspa = max(t.max(), 0.0)
    Z = np.sqrt(T) * (Mb - m) / om                            # centred bootstrap t
    thr = -np.sqrt(2 * np.log(np.log(T)))
    mu_c = np.where(t <= thr, m, 0.0); mu_l = np.minimum(m, 0.0)          # Hansen g_c: recentre only clearly bad models
    def pv(mu):
        st = np.maximum((np.sqrt(T) * mu / om)[None, :] + Z, 0).max(axis=1)
        return float(np.mean(st >= Tspa))
    out = dict(T_spa=float(Tspa), p_consistent=pv(mu_c), p_upper=pv(np.zeros(N)), p_lower=pv(mu_l))
    # Romano-Wolf step-down (studentized)
    rej = np.zeros(N, bool); steps = []
    while True:
        act = ~rej
        if not act.any(): break
        c = np.quantile(Z[:, act].max(axis=1), 1 - ALPHA)
        new = act & (t > c)
        steps.append(dict(crit=float(c), new=int(new.sum())))
        if not new.any(): break
        rej |= new
    out.update(rw_rejected=int(rej.sum()), rw_steps=steps[:10], rw_ids=[int(i) for i in np.flatnonzero(rej)][:200])
    out['t'] = t; out['mean'] = m
    return out


def eff_n(D):
    Z = (D - D.mean(axis=0)) / np.where(D.std(axis=0) > 0, D.std(axis=0), 1)
    s = np.linalg.svd(Z.astype(np.float64), compute_uv=False)
    lam = s ** 2 / Z.shape[0]
    pr = float(lam.sum() ** 2 / (lam ** 2).sum())
    n95 = int(np.searchsorted(np.cumsum(lam) / lam.sum(), 0.95) + 1)
    # leader clustering rho >= 0.9 (rules in order of decreasing mean)
    order = np.argsort(-D.mean(axis=0))
    Zn = (Z / np.sqrt(Z.shape[0])).astype(np.float64)
    L = np.zeros((Z.shape[0], Z.shape[1])); nlead = 0
    for i in order:
        z = Zn[:, i]
        if nlead and np.max(z @ L[:, :nlead]) >= 0.9: continue
        L[:, nlead] = z; nlead += 1
    return dict(pr=pr, n95=n95, leaders_rho09=int(nlead))


def dsr(D, k, N):
    x = D[:, k].astype(np.float64); T = len(x)
    SR = D.mean(axis=0) / np.where(D.std(axis=0, ddof=1) > 0, D.std(axis=0, ddof=1), np.inf)
    V = float(np.var(SR, ddof=1)); g = 0.5772156649
    sr0 = np.sqrt(V) * ((1 - g) * norm.ppf(1 - 1.0 / N) + g * norm.ppf(1 - 1.0 / (N * np.e)))
    sr = x.mean() / x.std(ddof=1); g3 = skew(x); g4 = kurtosis(x, fisher=False)
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    return dict(SR_monthly=float(sr), SR_ann=float(sr * np.sqrt(12)), SR0=float(sr0), N=float(N), V=V, skew=float(g3), kurt=float(g4), DSR=float(norm.cdf(z)))


if __name__ == '__main__':
    D = np.load(S + 'results/disc_D.npy'); D85 = np.load(S + 'results/disc_D085.npy')
    meta = json.load(open(S + 'results/disc_meta.json'))
    ok = np.array([c is not None for c in meta['cagr']])
    T, N = D.shape
    C = sb_counts(T, B, MB, SEED)
    A = spa_rw(D, C); A85 = spa_rw(D85, C)
    m = A['mean']; best = int(np.argmax(m)); bestSR = int(np.argmax(m / D.std(axis=0, ddof=1)))
    E = eff_n(D)
    res = dict(T=T, N=N, N_ok=int(ok.sum()), B=B, mean_block=MB, seed=SEED,
               spa_vs_1x={k: v for k, v in A.items() if k not in ('t', 'mean')},
               spa_vs_s085={k: v for k, v in A85.items() if k not in ('t', 'mean')}, eff_n=E,
               best_mean=dict(id=best, mean_m=float(m[best]), ann_log=float(12 * m[best]), t=float(A['t'][best]),
                              in_rw=bool(best in set(A['rw_ids'])), mean_vs_s085_ann=float(12 * A85['mean'][best]),
                              dsr_Ntot=dsr(D, best, N), dsr_pr=dsr(D, best, E['pr']), dsr_lead=dsr(D, best, E['leaders_rho09'])),
               best_sr=dict(id=bestSR, ann_log=float(12 * m[bestSR]), dsr_Ntot=dsr(D, bestSR, N), dsr_lead=dsr(D, bestSR, E['leaders_rho09'])),
               best_vs_s085=dict(id=int(np.argmax(A85['mean'])), ann_log=float(12 * A85['mean'].max()), t=float(A85['t'].max())),
               top20=[int(i) for i in np.argsort(-m)[:20]],
               n_pos_1x=int((m > 0).sum()), n_pos_s085=int((A85['mean'] > 0).sum()),
               quantiles_ann_vs_1x=[float(12 * np.quantile(m, q)) for q in (0.5, 0.9, 0.99, 0.999, 1.0)],
               quantiles_ann_vs_s085=[float(12 * np.quantile(A85['mean'], q)) for q in (0.5, 0.9, 0.99, 0.999, 1.0)])
    json.dump(res, open(S + 'results/stats.json', 'w'), indent=1)
    np.save(S + 'results/disc_t.npy', np.c_[A['t'], A85['t']])
    print(json.dumps({k: res[k] for k in ('spa_vs_1x', 'spa_vs_s085', 'eff_n', 'best_mean', 'best_vs_s085', 'quantiles_ann_vs_1x', 'quantiles_ann_vs_s085')}, indent=1)[:6000])
