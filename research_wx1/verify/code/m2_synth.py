import numpy as np
def boot(n, B=1000, seed=20261104):
    rng = np.random.default_rng(seed); Cnt = np.zeros((B, n))
    for b in range(B):
        idx = np.empty(n, np.int64); idx[0] = rng.integers(n)
        for t in range(1, n):
            idx[t] = rng.integers(n) if rng.random() < 1/3 else (idx[t-1]+1) % n
        Cnt[b] = np.bincount(idx, minlength=n)
    return Cnt
n = 168; Cnt = boot(n); rng = np.random.default_rng(3)
def pvals(X):
    dbar = X.mean(0); Ds = Cnt @ X / n; om = np.maximum(np.sqrt(n)*Ds.std(0, ddof=1), 1e-12)
    t = np.sqrt(n)*dbar/om; T = max(0, t.max()); thr = -np.sqrt(2*np.log(np.log(n)))
    worker = np.maximum(0, (np.sqrt(n)*(Ds - dbar + np.where(t >= thr, dbar, 0))/om).max(1))
    hansen = np.maximum(0, (np.sqrt(n)*(Ds - np.where(t >= thr, dbar, 0))/om).max(1))
    return (worker >= T).mean(), (hansen >= T).mean(), t[0]
for tt in (0.0, 4.0, 6.0, 8.0):
    out = []
    for rep in range(30):
        f = rng.normal(size=(n, 3)); L = rng.normal(size=(3, 2000))
        X = f @ L * 0.5 + rng.standard_t(5, size=(n, 2000))
        X[:, 0] += tt * X[:, 0].std() / np.sqrt(n)
        out.append(pvals(X))
    o = np.array(out)
    print('planted t=%.0f: worker p_c median %.3f (P<.05 %.2f) | Hansen p_c median %.3f (P<.05 %.2f)' % (tt, np.median(o[:, 0]), (o[:, 0] < .05).mean(), np.median(o[:, 1]), (o[:, 1] < .05).mean()))
