# NI1-B data-quality diagnostic (no returns): does signal=1 at t predict an OAP announcement in month t+1?
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/bt1/ni1/B/code'); import fl_common as F
dates, adj, mem = F.load_panel(); ym, me, months = F.month_index(dates)
oap = pd.read_parquet(sys.argv[1]); oap = oap[oap.yyyymm <= 201412]
I, R, pidx = F.announcement_matrix(oap, months); L = F.link_by_month(mem[me], R, pidx)
k0 = F.ym_to_m(197412) - months[0]; k1 = F.ym_to_m(201411) - months[0]
h1 = n1 = h0 = n0 = 0; out = {}
for k in range(k0, k1 + 1):
    js = L[k][L[k] >= 0]
    sig = I[k - 11, js] & ~I[k, js] & (I[k - 11:k + 1, js].sum(0) == 4)
    a = I[k + 1, js]
    h1 += (a & sig).sum(); n1 += sig.sum(); h0 += (a & ~sig).sum(); n0 += (~sig).sum()
out = dict(p_announce_next_given_sig1=h1 / n1, p_announce_next_given_sig0=h0 / n0)
json.dump({k: float(v) for k, v in out.items()}, open(sys.argv[2], 'w'), indent=1); print(out)
