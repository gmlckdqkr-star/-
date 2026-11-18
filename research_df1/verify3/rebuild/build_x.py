"""Independent rebuild of the DF3 X world (extreme-crash-free bootstrap) from PRECOMMIT_DF3.md sections 1-2 only."""
import os, sys, json
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import numpy as np, pandas as pd
import dfctx as DC
from dfctx import std

iv = std.iv
a,b,P,blk,seed = iv.POOLS['dev250']
R,M = std.jp.calendar(a,b)
X = std.jp.mkX(R,M,'NDX')
assert X.index.max() <= pd.Timestamp('2014-12-31')
lvl = (1 + X['r'].fillna(0)).cumprod()
idx = X.index; n = len(X)

def pos(d): return int(idx.get_loc(d))
def win(s, e): return lvl[(idx >= pd.Timestamp(s)) & (idx <= pd.Timestamp(e))]

eps = {}
# E1: trough = min close 1987-10-01..1987-12-31; peak = max 1987 close before trough
tr = win('1987-10-01','1987-12-31').idxmin()
pk = win('1987-01-01', tr).idxmax()
eps['E1'] = (pk, tr)
# E2: peak = max close in 2000; trough = min close 2000-01-01..2003-12-31
pk = win('2000-01-01','2000-12-31').idxmax(); tr = win('2000-01-01','2003-12-31').idxmin()
eps['E2'] = (pk, tr)
# E3: peak = max 2007-01-01..2008-06-30; trough = min 2008-07-01..2009-06-30
pk = win('2007-01-01','2008-06-30').idxmax(); tr = win('2008-07-01','2009-06-30').idxmin()
eps['E3'] = (pk, tr)

keep = np.ones(n, bool)
ep_out = {}
for k,(pk,tr) in eps.items():
    ip, it = pos(pk), pos(tr); ie = min(it + 250, n - 1)
    keep[ip:ie+1] = False
    ep_out[k] = dict(peak=str(pk.date()), trough=str(tr.date()), peak_i=ip, trough_i=it, end_i=ie,
                     end=str(idx[ie].date()), dd=float(lvl.iloc[it]/lvl.iloc[ip]-1), n_excl=ie-ip+1)

# kept segments (contiguous runs of kept indices)
segs = []; i = 0
while i < n:
    if keep[i]:
        j = i
        while j + 1 < n and keep[j+1]: j += 1
        segs.append((i, j)); i = j + 1
    else: i += 1

L = 250
starts = np.array([s for s in range(1, n - 251 + 1) if keep[s:s+L].all()], dtype=np.int64)

g = np.random.default_rng(7)
T = 300 + 30*252; nb = T//250 + 1
st = starts[g.integers(0, len(starts), (500, nb))]
ii = (st[:,:,None] + np.arange(250)).reshape(500,-1)[:, :T]
assert keep[ii].all()
np.save('/tmp/vf_rebuild/ii_mine.npy', ii)

out = dict(n=n, episodes=ep_out,
           kept_segments=[dict(i0=int(s), i1=int(e), d0=str(idx[s].date()), d1=str(idx[e].date()), len=int(e-s+1)) for s,e in segs],
           n_kept=int(keep.sum()), n_allowed_starts=int(len(starts)), starts_first=int(starts[0]), starts_last=int(starts[-1]),
           T=T, nb=nb, ii_shape=list(ii.shape), ii_sum=int(ii.sum()), ii_first_row_head=ii[0,:5].tolist())
json.dump(out, open('/tmp/vf_rebuild/mine_construction.json','w'), indent=1)
print(json.dumps(out, indent=1))
