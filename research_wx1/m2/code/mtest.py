"""Multiple-testing control on the discovery grid (PRECOMMIT_M2 §6): Hansen SPA (consistent, studentized), Romano-Wolf
stepdown 5%, DSR with N and effective N (participation ratio / 95% PCs). Stationary bootstrap mean block 3 months,
1,000 reps, seed fixed. Writes summary json + top-20 ids for the one-shot confirmation.
argv: grid_disc.npz out_json top20_json"""
import sys, json, hashlib, numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis
z = np.load(sys.argv[1]); X = z['X']; RAW = z['RAW']; rew = z['rew']
VAR = json.loads(str(z['var']))
n, m = X.shape
ok = np.isfinite(X).all(0)
assert ok.all(), f'{(~ok).sum()} variants with missing months'
# duplicates (identical monthly series)
h = [hashlib.sha1(np.round(X[:, k], 12).tobytes()).hexdigest() for k in range(m)]
n_unique = len(set(h))
dbar = X.mean(0)
B, pblk, rng = 1000, 1.0 / 3.0, np.random.default_rng(20261104)
Cnt = np.zeros((B, n))
for b in range(B):
    idx = np.empty(n, np.int64); idx[0] = rng.integers(n)
    for t in range(1, n):
        idx[t] = rng.integers(n) if rng.random() < pblk else (idx[t - 1] + 1) % n
    Cnt[b] = np.bincount(idx, minlength=n)
Dstar = Cnt @ X / n                                         # [B, m] bootstrap means
omega = np.sqrt(n) * Dstar.std(0, ddof=1)
omega = np.maximum(omega, 1e-12)
tstat = np.sqrt(n) * dbar / omega
T_spa = max(0.0, float(tstat.max()))
thr = -np.sqrt(2 * np.log(np.log(n)))
mu_c = np.where(tstat >= thr, dbar, 0.0)
mu_l = np.minimum(dbar, 0.0) * 0 + 0.0                      # lower: g = max(dbar, 0)?  (Hansen: mu_l = 0 -> uses dbar - dbar)
Tb_c = np.maximum(0.0, (np.sqrt(n) * (Dstar - dbar + mu_c) / omega).max(1))
Tb_u = np.maximum(0.0, (np.sqrt(n) * (Dstar - dbar + dbar) / omega).max(1))     # upper (RC-like, mu = dbar)
Tb_l = np.maximum(0.0, (np.sqrt(n) * (Dstar - dbar + np.maximum(dbar, 0)) / omega).max(1))
p_c = float(np.mean(Tb_c >= T_spa)); p_u = float(np.mean(Tb_u >= T_spa)); p_l = float(np.mean(Tb_l >= T_spa))
# Romano-Wolf stepdown (studentized max over the remaining set)
Zc = np.sqrt(n) * (Dstar - dbar) / omega                    # centred bootstrap t
rem = np.ones(m, bool); rej = np.zeros(m, bool)
while True:
    c = np.quantile(Zc[:, rem].max(1), 0.95)
    new = rem & (tstat > c)
    if not new.any():
        break
    rej |= new; rem &= ~new
    if not rem.any():
        break
rw_c = float(c)
# effective N
Xs = (X - X.mean(0)) / X.std(0, ddof=1)
s = np.linalg.svd(Xs, compute_uv=False)
lam = s ** 2 / (n - 1)
pr = float(lam.sum() ** 2 / (lam ** 2).sum())
n95 = int(np.searchsorted(np.cumsum(lam) / lam.sum(), 0.95) + 1)
# selection: top by mean x
order = np.argsort(-dbar)
best = int(order[0])
sr = dbar / X.std(0, ddof=1)                                # monthly information ratio vs EW


def dsr(k, N):
    x = X[:, k]; S = sr[k]
    V = sr.var(ddof=1)
    g = 0.5772156649
    emax = np.sqrt(V) * ((1 - g) * norm.ppf(1 - 1.0 / N) + g * norm.ppf(1 - 1.0 / (N * np.e)))
    g3 = skew(x); g4 = kurtosis(x, fisher=False)
    den = np.sqrt(max(1e-12, 1 - g3 * S + (g4 - 1) / 4 * S ** 2))
    return float(norm.cdf((S - emax) * np.sqrt(n - 1) / den)), float(emax)


dsr_N, e_N = dsr(best, m); dsr_pr, e_pr = dsr(best, max(2, pr)); dsr_95, e_95 = dsr(best, max(2, n95))
yrs = n / 12.0


def cagr(r):
    return float(np.prod(1 + r) ** (1 / yrs) - 1)


top = [int(k) for k in order[:20]]
out = dict(N=m, N_unique=n_unique, n_months=n, T_spa=T_spa, spa_p_consistent=p_c, spa_p_upper=p_u, spa_p_lower=p_l,
           rw_reject=int(rej.sum()), rw_crit=rw_c, N_eff_pr=pr, N_eff_95=n95,
           best=dict(id=best, var=VAR[best], mean_x_month=float(dbar[best]), ann_excess_log=float(12 * dbar[best]),
                     t=float(tstat[best]), ir_month=float(sr[best]), ir_ann=float(sr[best] * np.sqrt(12)),
                     cagr_pretax_disc=cagr(RAW[:, best]), ew_cagr_pretax_disc=cagr(rew),
                     dsr_N=dsr_N, emax_sr_N=e_N, dsr_Neff_pr=dsr_pr, emax_sr_pr=e_pr, dsr_N95=dsr_95, in_rw=bool(rej[best])),
           top20=[dict(id=k, var=VAR[k], mean_x=float(dbar[k]), ann_excess_log=float(12 * dbar[k]), t=float(tstat[k]),
                       cagr_pretax_disc=cagr(RAW[:, k]), in_rw=bool(rej[k])) for k in top],
           dist=dict(share_pos=float((dbar > 0).mean()), q50=float(np.median(12 * dbar)), q90=float(np.quantile(12 * dbar, .9)),
                     q99=float(np.quantile(12 * dbar, .99)), max=float(12 * dbar.max()), min=float(12 * dbar.min()),
                     t_max=float(tstat.max())))
df = pd.DataFrame(VAR); df['ann_x'] = 12 * dbar; df['t'] = tstat
out['by_dim'] = {c: df.groupby(c)['ann_x'].agg(['mean', 'max']).round(4).to_dict('index') for c in ['S', 'W', 'SN', 'CF', 'C', 'K', 'Rb']}
json.dump(out, open(sys.argv[2], 'w'), indent=1, default=str)
json.dump(top, open(sys.argv[3], 'w'))
np.save(sys.argv[2].replace('.json', '_meanx.npy'), dbar)
print(json.dumps({k: v for k, v in out.items() if k not in ('top20', 'by_dim')}, indent=1, default=str))
for r in out['top20'][:20]:
    print(r)
for c, v in out['by_dim'].items():
    print(c, v)
