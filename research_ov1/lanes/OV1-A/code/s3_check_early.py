"""OV1-A implementation check, EARLY data only (<=1999-12-31): brute-force loop vs vectorized on-rule, on-days by year,
spike ratio by year, on-blocks for all v1 states. Diagnostic only (no new variant, not in N)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-A/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import sig_a, ov1lib as L, gate, ov  # noqa
X = sig_a.ndx_X(); cal = X.index; E = pd.Timestamp('1999-12-31')
Ns = sig_a.noise_star(cal)[:E]; on = sig_a.on_series(Ns)
x = Ns.values; br = np.zeros(len(x), bool)
for t in range(251, len(x)):
    w = x[t - 251:t + 1]
    if np.isnan(w).any(): continue
    pk = x[t - 62:t + 1]; peak = pk.max(); k = t - 62 + np.where(pk == peak)[0].max(); base = np.median(w)
    br[t] = (peak >= 2 * base) and (x[t] <= base + .5 * (peak - base)) and (t - k >= 5)
print('brute == vectorized:', bool((br == on.values).all()), 'on days', int(on.sum()))
df = pd.DataFrame({'N': Ns, 'on': on, 'ratio': Ns.rolling(63).max() / Ns.rolling(252, min_periods=252).median()})
yr = df.groupby(df.index.year).agg(on_days=('on', 'sum'), max_ratio=('ratio', 'max'), medN=('N', 'median'))
print(yr.round(3).to_string())
# on episodes
s = on.astype(int); g = (s.diff() != 0).cumsum(); ep = [(str(v.index[0].date()), str(v.index[-1].date()), len(v)) for _, v in on[on].groupby(g[on])]
print('on episodes (start, end, days):', ep)
F = ov.flags_hist(X); i0 = cal.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
print('v1 B share of days 1988-1999:', B['1988-01-04':E].value_counts(normalize=True).round(3).to_dict())
print('v1 B during on-days:', B.reindex(on[on].index).value_counts().to_dict())
lab = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02'); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
blk = lab[(lab.index >= pd.Timestamp('1988-01-04')) & (end <= E)]
ob = on.reindex(blk.index).fillna(False)
print('early blocks with on at start (any v1 state):', int(ob.sum()), [(str(d.date()), float(B[d])) for d in blk.index[ob.values]])
json.dump(dict(brute_equal=bool((br == on.values).all()), on_days_early=int(on.sum()), episodes=ep,
               yearly={int(k): {kk: float(vv) for kk, vv in r.items()} for k, r in yr.iterrows()},
               v1B_on_days={str(k): int(v) for k, v in B.reindex(on[on].index).value_counts().items()},
               on_blocks_any_state=[(str(d.date()), float(B[d])) for d in blk.index[ob.values]]),
          open('/mnt/project-files/research/ov1/lanes/OV1-A/results/s3_check_early.json', 'w'), indent=1)
