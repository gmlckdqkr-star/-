"""D2: on all MS1 bases, per path-year (252-day blocks) gap s0.85 vs 1x index, attribution by mechanism.
mechanisms (log contributions vs 1x, summed over the year):
  cash   = days held at 0 : log(1+cash) - log(1+r)           (missing up-days / dodging down-days)
  dir3   = days held >1 : (L-1)*r direction part                (levered direction)
  drag   = days held >1 : remainder of frictionless log gap      (vol drag + financing + 3x fee)
  mid    = days held 0<L<=1 (1x via 1/3 TQQQ + cash)
  fric   = actual - frictionless (trading cost, yearly tax paid, intra-hold drift)
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/s085_weak/code'); import wk
C = wk.std.contexts(); W = wk.WARM
out = {}
for bn, c in C.items():
    B, bfn, bp, fs = wk.std.s085(c)
    o, E, CU, TG, BB = wk.run(c, B, bfn, bp, fs)
    r = c.r[:, W:]; rf = c.rf[:, W:]
    lp = np.concatenate([np.zeros((r.shape[0], 1)), CU[:, :-1]], axis=1)
    cash = np.maximum(rf - 0.02 / 252, 0) * (1 - 0.154); w0 = lp / 3
    g = w0 * (3 * r - 2 * rf - 0.0245 / 252) + (1 - w0) * cash
    ge = np.concatenate([np.zeros((r.shape[0], 1)), E[:, 1:] / E[:, :-1] - 1], axis=1)
    lg = np.log1p(g) - np.log1p(r); fr = np.log1p(ge) - np.log1p(g)
    z = lp == 0; hi = lp > 1.01; mid = (lp > 0) & ~hi
    dirp = np.where(hi, (lp - 1) * r, 0.0)
    comp = dict(cash=np.where(z, lg, 0), dir3=dirp, drag=np.where(hi, lg - dirp, 0), mid=np.where(mid, lg, 0), fric=fr)
    brk = BB - TG
    T = r.shape[1]; ny = T // 252
    def yr(a): return a[:, :ny * 252].reshape(a.shape[0], ny, 252).sum(axis=2)
    gap = yr(np.log1p(ge) - np.log1p(r)); idx = yr(np.log1p(r))
    Y = {k: yr(v) for k, v in comp.items()}; brY = brk[:, :ny * 252].reshape(-1, ny, 252).mean(axis=2)
    lag = gap < 0
    res = dict(years=int(gap.size), lag_frac=float(lag.mean()), lag_frac_idx_up=float(lag[idx > 0].mean()),
               lag_frac_idx_down=float(lag[idx <= 0].mean()) if (idx <= 0).any() else None,
               mean_gap=float(gap.mean()), mean_gap_lagyears=float(gap[lag].mean()))
    # share of total lag (sum of gap over lag years) by mechanism
    tot = gap[lag].sum()
    res['lag_share'] = {k: float(v[lag].sum() / tot) for k, v in Y.items()}
    res['lag_mean_by_mech'] = {k: float(v[lag].mean()) for k, v in Y.items()}
    res['win_mean_by_mech'] = {k: float(v[~lag].mean()) for k, v in Y.items()}
    # dominant mechanism of each lag year (most negative component)
    keys = list(Y); M = np.stack([Y[k] for k in keys], -1); dom = np.argmin(M, -1)
    res['dominant'] = {k: float(np.mean(dom[lag] == i)) for i, k in enumerate(keys)}
    res['brake_avg_lag'] = float(brY[lag].mean()); res['brake_avg_win'] = float(brY[~lag].mean())
    # index-year buckets
    b = pd.cut(idx.ravel(), [-9, -0.2, -0.05, 0.05, 0.15, 9], labels=['<-20', '-20..-5', '-5..+5', '+5..+15', '>15'])
    res['by_index_year'] = {str(k): dict(n=int((b == k).sum()), lag_frac=float(lag.ravel()[b == k].mean()), mean_gap=float(gap.ravel()[b == k].mean()))
                            for k in b.categories}
    # rolling horizons: P(s0.85 behind 1x after h years) using cumulative log gap from year 0 and from all starts
    cg = np.cumsum(gap, axis=1)
    res['behind_h'] = {}
    for h in (1, 3, 5, 10):
        if h <= ny:
            v = [cg[:, s + h - 1] - (cg[:, s - 1] if s > 0 else 0) for s in range(0, ny - h + 1)]
            res['behind_h'][h] = float(np.mean(np.concatenate(v) < 0))
    out[bn] = res
    print(bn, json.dumps(res, indent=None)[:1500], flush=True)
json.dump(out, open('/mnt/project-files/research/s085_weak/results/d2_paths.json', 'w'), indent=1)
