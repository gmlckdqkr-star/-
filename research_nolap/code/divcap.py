"""N3 dividend capture under KR tax asymmetry (div 15.4%, price P&L 22% with full offset = generous). K1: buy close d-1, sell close d (ex-date d). K5: sell close d+4."""
import numpy as np, pandas as pd, json
z = np.load('/tmp/claude-0/fx/panel.npz', allow_pickle=True)
dates = pd.to_datetime(z['dates'], unit='D'); T = len(dates)
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool); adj = z['adj'].astype(np.float64); divy = np.nan_to_num(z['divy'].astype(np.float64))
r = np.full_like(adj, np.nan); r[1:] = adj[1:] / adj[:-1] - 1
EW = np.r_[0, np.nan_to_num(np.nanmean(np.where(mem[:-1], r[1:], np.nan), axis=1))]
out = {}
for K in (1, 5):
    d, j = np.nonzero((divy > 0) & np.r_[np.zeros((1, mem.shape[1]), bool), mem[:-1]])
    keep = (d + K - 1 < T) & (dates[d].year >= 1986)
    d, j = d[keep], j[keep]
    tot = adj[d + K - 1, j] / adj[d - 1, j] - 1; D = divy[d, j]; ok = np.isfinite(tot); tot, D, dd = tot[ok], D[ok], d[ok]
    P = tot - D   # price-only change
    ew = np.array([np.prod(1 + EW[x:x + K]) - 1 for x in dd])
    at = 0.846 * D + 0.78 * P - 0.78 * 0.006
    o = dict(n=int(len(D)), div_mean=float(D.mean()), div_med=float(np.median(D)), price_mean=float(P.mean()), drop_ratio=float(-P.mean() / D.mean()),
             aftertax_mean=float(at.mean()), ew_aftertax=float((0.78 * ew).mean()), excess_mean=float((at - 0.78 * ew).mean()),
             excess_nocost=float((at + 0.78 * 0.006 - 0.78 * ew).mean()), frac_D_gt_1pct=float((D > 0.01).mean()))
    hi = D > 0.02; o.update(hi_n=int(hi.sum()), hi_excess=float((at - 0.78 * ew)[hi].mean()) if hi.any() else None)
    out['K%d' % K] = o; print('K%d' % K, ' '.join('%s=%s' % (k, ('%.5f' % v) if isinstance(v, float) else v) for k, v in o.items()))
json.dump(out, open('/mnt/project-files/research/nolap/results/n3_divcap.json', 'w'), indent=1)
