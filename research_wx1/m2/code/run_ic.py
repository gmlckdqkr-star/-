"""Information first (PRECOMMIT_M2 §7): monthly rank IC of the composite (ALL) and per group in DISCOVERY (decisions
1986-01..1999-12) only. Caches per-signal IC and rank correlation matrices (needed for past-only weights).
argv: code_dir out_json"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[1])
import m2lib as M
t0 = time.time()
d = M.load()
RR = M.ranks_ret(d)
ic = M.signal_ic(d, RR)
C = M.signal_corr(d)
np.savez(M.SCR + '/ic_cache.npz', ic=ic, C=C, RR=RR)
print('cached', time.time() - t0, flush=True)
disc = (d.yr >= 1986) & (d.yr <= 1999)
est = M.past_means(ic, C)
sub = M.subsets(d)
out = {}


def stat(x):
    x = x[disc]; x = x[np.isfinite(x)]
    return dict(mean=round(float(x.mean()), 4), t=round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2), n=int(len(x)))


for name in ['ALL'] + M.GNAMES + ['CLEAR', 'TOPT']:
    row = {}
    for wk in ('EQ', 'ICW', 'RIDGE'):
        W = M.weights(d, sub[name], wk, None if wk == 'EQ' else est)
        sc = M.composite(d, W)
        row[wk] = stat(M.ic_series(d, sc, RR))
    row['n_usable_1986'] = int(d.U[np.argmax(d.yr >= 1986)][sub[name]].sum())
    row['n_usable_1999'] = int(d.U[np.flatnonzero(d.yr == 1999)[-1]][sub[name]].sum())
    out[name] = row
    print(name, row, flush=True)
# single usable signals in discovery: distribution of mean IC (only months where usable)
sing = {}
for s in np.flatnonzero(d.keep):
    m = disc & d.U[:, s] & np.isfinite(ic[:, s])
    if m.sum() >= 12:
        x = ic[m, s]
        sing[str(d.cols[s])] = dict(mean=round(float(x.mean()), 4), t=round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2), n=int(m.sum()))
out['single_signals_disc'] = sing
v = np.array([x['mean'] for x in sing.values()])
out['single_summary'] = dict(n=len(v), max=float(v.max()), median=float(np.median(v)), n_pos=int((v > 0).sum()))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(out['single_summary'], sorted(sing.items(), key=lambda kv: -kv[1]['mean'])[:8], time.time() - t0)
