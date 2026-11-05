# NI1-B step 2: choose the one-month shift (0 or -1) on 2008-2014 only, by matching the raw OAP announcement month
# to the month with the larger |market-adjusted monthly return|. No signal forward returns are used.
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/bt1/ni1/B/code'); import fl_common as F
oap_p, out = sys.argv[1], sys.argv[2]
dates, adj, mem = F.load_panel()
ym, me, months = F.month_index(dates)
oap = pd.read_parquet(oap_p); oap = oap[oap.yyyymm <= 201412]
I, R, pidx = F.announcement_matrix(oap, months)
memME = mem[me]
L = F.link_by_month(memME, R, pidx)
P = adj[me]; r = np.full_like(P, np.nan); r[1:] = P[1:] / P[:-1] - 1      # r[k] = return over month k
mk = np.full(len(months), np.nan)
for k in range(1, len(months)):
    ok = memME[k - 1] & np.isfinite(r[k]); mk[k] = r[k, ok].mean() if ok.any() else np.nan
mar = r - mk[:, None]
lo, hi = F.ym_to_m(200801) - months[0], F.ym_to_m(201412) - months[0]
v0 = v1 = 0
for k in range(lo, hi + 1):
    for c in np.where(L[k - 2] >= 0)[0]:          # member & linked at end of month A-2
        j = L[k - 2, c]
        if not I[k, j]: continue
        a, b = mar[k, c], mar[k - 1, c]
        if not (np.isfinite(a) and np.isfinite(b)): continue
        if abs(a) > abs(b): v0 += 1
        else: v1 += 1
shift = 0 if v0 >= v1 else -1
res = {'window': '2008-01..2014-12 raw OAP announcement months', 'events': v0 + v1,
       'votes_shift0_month_A_larger': v0, 'votes_shiftm1_month_Aminus1_larger': v1,
       'share_shift0': v0 / (v0 + v1), 'chosen_shift': shift}
json.dump(res, open(out, 'w'), indent=1); print(res)
