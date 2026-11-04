"""D1: yearly s0.85 vs 1x index on real paths; per-year attribution of the log gap by held level bucket and friction."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/s085_weak/code'); import wk
C = wk.std.contexts(); DT = wk.real_dates(); W = wk.WARM
rows = []
for bn in ('real_ndx_86_14', 'real_spx_55_85'):
    c = C[bn]; B, bfn, bp, fs = wk.std.s085(c)
    o, E, CU, TG, BB = wk.run(c, B, bfn, bp, fs)
    o0, E0, CU0, _, _ = wk.run(c, B, bfn, bp, fs, tax=0.0, cost=0.0)   # frictionless twin (same path dependence? brake sees E -> may differ)
    r = c.r[0, W:]; rf = c.rf[0, W:]; d = DT[bn]; e = E[0]; cu = CU[0]; tg = TG[0]; bb = BB[0]
    lev_prev = np.r_[0, cu[:-1]]           # level earning day k's return
    cash = np.maximum(rf - 0.02 / 252, 0) * (1 - 0.154)
    w0 = lev_prev / 3
    g = w0 * (3 * r - 2 * rf - 0.0245 / 252) + (1 - w0) * cash     # frictionless (ignores intra-hold drift)
    ge = np.r_[0, e[1:] / e[:-1] - 1]
    fric = np.log1p(ge) - np.log1p(g)
    yr = d.year
    for y in np.unique(yr):
        m = yr == y
        if m.sum() < 120: continue
        idx = np.prod(1 + r[m]) - 1; s = np.prod(1 + ge[m]) - 1; s3 = np.prod(1 + 3 * r[m] - 2 * rf[m] - 0.0245 / 252) - 1
        gap = np.log1p(s) - np.log1p(idx)
        lp = lev_prev[m]; rr = r[m]; gg = g[m]
        att = {}
        for nm, sel in (('L0', lp == 0), ('L<=1', (lp > 0) & (lp <= 1.01)), ('L1-2.5', (lp > 1.01) & (lp < 2.49)), ('L3', lp >= 2.49)):
            att[nm] = float(np.sum(np.log1p(gg[sel]) - np.log1p(rr[sel])))
        att['fric'] = float(np.sum(fric[m]))
        brake = float(np.mean(bb[m] - tg[m]))  # avg level removed by brake
        rows.append(dict(basis=bn, year=int(y), idx=idx, s085=s, hold3=s3, gap=gap, avgL=float(lp.mean()), cash=float(np.mean(lp == 0)),
                         at3=float(np.mean(lp >= 2.49)), sig=float(bb[m].mean()), brake=brake, **att))
df = pd.DataFrame(rows)
df.to_csv('/mnt/project-files/research/s085_weak/results/d1_years.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(df.round(3).to_string())
