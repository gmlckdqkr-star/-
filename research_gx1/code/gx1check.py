"""GX1 pre-compute checks (no strategy performance): C3 dates, C4 strict as-of vs an independent merge_asof on every row,
C5 path identity (ii = original order), C5b block-join perturbation, coverage."""
import numpy as np, pandas as pd, json, sys
sys.path.insert(0, '/mnt/project-files/research/gx1/code'); import gx1lib as G
out = {}
for m in G.MARKETS: G.index(m)                                                      # C3 asserts inside
cal = pd.DatetimeIndex(G.jp.calendar('1984-01-03', '2014-12-31')[0].index); assert cal.max() <= G.END
mk = G.signal_set('US'); L, AGE = G.asof_levels(cal, mk); bad = 0
left = pd.DataFrame({'t': cal})
for j, m in enumerate(mk):                                                          # C4: independent implementation
    s = G.index(m).rename('c').reset_index().rename(columns={'date': 'd'})
    mg = pd.merge_asof(left, s, left_on='t', right_on='d', allow_exact_matches=False)
    ok = (mg['t'] - mg['d']).dt.days <= G.BREAK_DAYS
    ref = np.where(ok, mg['c'].values, np.nan)
    bad += int((~((np.isnan(ref) & np.isnan(L[:, j])) | (ref == L[:, j]))).sum())
out['C4_mismatch_cells'] = bad; out['C4_markets'] = len(mk)
D = G.world_signals(cal, 'US'); ii = np.arange(len(cal))[None, :]; Pw = G.path_world(cal, ii, 'US')
out['C5_identity_mismatch_rows'] = {('%s>=%.2f' % G.SIGNALS[i]): int((D['G%02d' % i].values != Pw['G%02d' % i][0]).sum()) for i in range(13)}
a, b, P, blk, seed = G.iv.POOLS['dev250']; cal2 = pd.DatetimeIndex(G.jp.calendar(a, b)[0].index)
ii2 = G.ov.boot_idx(len(cal2), P=3, years=30, block=blk, seed=seed, lo=1)
base = G.path_world(cal2, ii2, 'US'); L2, _ = G.asof_levels(cal2, G.signal_set('US'))
used = np.zeros(len(cal2), bool); used[ii2.ravel()] = True; used[np.clip(ii2.ravel() - 1, 0, None)] = True
Lp = L2.copy(); rng = np.random.default_rng(3); Lp[~used] = np.where(np.isnan(Lp[~used]), np.nan, rng.uniform(1, 1e4, Lp[~used].shape))
pert = G.path_world(cal2, ii2, 'US', L_override=Lp)
out['C5b_perturb_changed_cells'] = int(sum((base['G%02d' % i] != pert['G%02d' % i]).sum() for i in range(10)))
out['C5b_unused_rows'] = int((~used).sum())
yr = cal.year
out['valid_markets_median_by_year_US'] = {k: {int(y): float(v) for y, v in D['n_' + k].groupby(yr).median().items() if y in (1988, 1989, 1990, 1994, 1998, 2002, 2008, 2014)} for k in ('B200', 'D20', 'N126', 'INV')}
print(json.dumps(out, indent=1)); json.dump(out, open('/mnt/project-files/research/gx1/results/precheck.json', 'w'), indent=1)
