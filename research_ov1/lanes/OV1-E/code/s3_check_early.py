"""OV1-E independent re-computation of ON on every EARLY-window block date (direct lookups into the raw <=2014 cut files,
explicit 1260-value windows, np.percentile), compared with the vectorized sig_e path used by s2_killA.py.
Also a second whole-day check with pandas rolling quantile over 1976-03-31..1999-12-31 only (no 2000+ day is compared)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-E/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import sig_e, gate, jp  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-E/'
MCAL = sig_e.master_cal(); TED = sig_e.ted_star(MCAL); ON, X, Q = sig_e.on_series(TED)
# independent raw reader (csv module path through pandas, '.'/blank -> drop), last obs strictly before date
def raw(sid):
    d = pd.read_csv(sig_e.D + 'cut_%s_le2014.csv' % sid, dtype=str); d.columns = ['date', 'v']; d['v'] = d['v'].fillna('')
    d = d[d['v'].str.strip().str.match(r'^-?[0-9.]+$') & (d['v'].str.strip() != '.')]
    return list(zip(pd.to_datetime(d['date']), d['v'].astype(float)))
RD = raw('DED3'); RT = raw('DTB3')
DD = np.array([a for a, _ in RD], 'datetime64[ns]'); DV = np.array([b for _, b in RD])
TD = np.array([a for a, _ in RT], 'datetime64[ns]'); TV = np.array([b for _, b in RT])
def ted_at(day):
    i = np.searchsorted(DD, np.datetime64(day), 'left') - 1; j = np.searchsorted(TD, np.datetime64(day), 'left') - 1
    return (DV[i] - TV[j]) if (i >= 0 and j >= 0) else np.nan
cal = MCAL; out = {}
for stream, a, b, st, lo, hi in (('SPX', '1928-01-03', '1985-12-31', '1955-01-03', '1976-03-31', '1985-12-31'),
                                 ('NDX', '1984-01-03', '2014-12-31', '1986-01-02', '1986-01-02', '1999-12-31')):
    lab = gate._frame(stream, a, b, st); R, M = jp.calendar(a, b); ec = R.index
    pos = ec.get_indexer(lab.index); end = ec[np.minimum(pos + 23, len(ec) - 1)]
    m = (lab.index >= pd.Timestamp(lo)) & (end <= pd.Timestamp(hi)); mism = 0; n = 0; maxdq = 0.0
    for t in lab.index[m]:
        j = cal.get_loc(t)
        xs = np.array([ted_at(cal[k]) - ted_at(cal[k - 63]) for k in range(j - 1260, j + 1)])
        valid = not np.isnan(xs).any()
        q = np.percentile(xs[:-1], 90) if valid else np.nan
        on_bf = bool(valid and xs[-1] > q); n += 1; mism += int(on_bf != bool(ON[t]))
        if valid: maxdq = max(maxdq, abs(q - Q[t]))
    out[stream] = dict(n_checked=n, mismatches=mism, max_abs_q90_diff=maxdq)
xs = pd.Series(X.values, index=cal)
qp = xs.shift(1).rolling(1260, min_periods=1260).quantile(0.9, interpolation='linear')
onp = (xs > qp) & xs.notna() & qp.notna()
w = (cal >= pd.Timestamp('1976-03-31')) & (cal <= pd.Timestamp('1999-12-31'))
out['whole_day_check_1976_1999'] = dict(days=int(w.sum()), mismatches=int((onp[w] != ON[w]).sum()),
                                        max_abs_q90_diff=float(np.nanmax(np.abs(qp[w].values - Q[w].values))))
o = ON[w]; out['on_day_share_1976_1999'] = float(o.mean())
out['on_day_share_by_year_1976_1999'] = {int(y): round(float(v), 3) for y, v in o.groupby(o.index.year).mean().items()}
print(json.dumps(out, indent=1)); json.dump(out, open(LANE + 'results/s3_check_early.json', 'w'), indent=1)
