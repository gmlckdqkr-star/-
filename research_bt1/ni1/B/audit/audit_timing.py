# NI1-B audit diagnostics (no signal forward returns): announcement-gap distribution, and where the largest
# |daily return| of linked members falls around the OAP change month A (A-1, A, A+1). Usage: python -I audit_timing.py <oap> <out>
import sys, io, lzma, json
import numpy as np, pandas as pd
OAP, OUT = sys.argv[1], sys.argv[2]
z = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz').read()))
dates = pd.to_datetime(z['dates'], unit='D'); adj = z['adj'].astype(float); T = len(dates)
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
mid = (dates.year * 12 + dates.month - 1).to_numpy()
o = pd.read_parquet(OAP); o = o[o.yyyymm <= 201412]
o['mid'] = (o.yyyymm // 100) * 12 + o.yyyymm % 100 - 1
nn = o[o.AnnouncementReturn.notna()].sort_values(['permno', 'mid']).copy()
nn['prev'] = nn.groupby('permno').AnnouncementReturn.shift(1)
ev = nn[nn.prev.notna() & (nn.AnnouncementReturn != nn.prev)].copy()
ev['gap'] = ev.groupby('permno').mid.diff()
gap = ev.gap.value_counts(normalize=True).sort_index().head(8).round(4).to_dict()
# run-length of a constant AR (how many months OAP carries one value forward)
lk = pd.read_csv('/mnt/project-files/research/influence/results/link_permno_col.csv')
lk = lk[~lk.col.duplicated(keep=False) & ~lk.permno.duplicated(keep=False)]   # unambiguous 1:1 links only (diagnostic)
p2c = dict(zip(lk.permno, lk.col))
lr = np.full_like(adj, np.nan); lr[1:] = np.log(adj[1:] / adj[:-1])
mkt = np.nanmean(np.where(mem, lr, np.nan), 1)
ab = np.abs(lr - mkt[:, None])
first_day = {m: i for i, m in reversed(list(enumerate(mid)))}
last_day = {m: i for i, m in enumerate(mid)}
cnt = {'all': np.zeros(3), '2008-14': np.zeros(3)}
match3 = {'all': np.zeros(3)}
for p, m, arv in zip(ev.permno.values, ev.mid.values, ev.AnnouncementReturn.values):
    c = p2c.get(p)
    if c is None or (m - 1) not in first_day or (m + 1) not in last_day: continue
    a, b = first_day[m - 1], last_day[m + 1]
    if not mem[a:b + 1, c].all(): continue
    seg = ab[a:b + 1, c]
    if not np.isfinite(seg).all(): continue
    which = mid[a + int(np.argmax(seg))] - (m - 1)      # 0 = A-1, 1 = A, 2 = A+1
    cnt['all'][which] += 1
    if 2008 * 12 <= m <= 2014 * 12 + 11: cnt['2008-14'][which] += 1
    # day whose 3-day [-1,+1] raw log return is closest to OAP AR value
    r3 = lr[a:b + 1, c]; s3 = np.convolve(r3, np.ones(3), 'same')
    which3 = mid[a + int(np.argmin(np.abs(s3 - arv)))] - (m - 1)
    match3['all'][which3] += 1
res = dict(gap_months_share=gap,
           max_abs_daily_abret_month={k: dict(zip(['A-1', 'A', 'A+1'], (v / v.sum()).round(4).tolist()), n=int(v.sum())) for k, v in cnt.items()},
           closest_3day_ret_to_AR_month={k: dict(zip(['A-1', 'A', 'A+1'], (v / v.sum()).round(4).tolist()), n=int(v.sum())) for k, v in match3.items()})
json.dump(res, open(OUT, 'w'), indent=1); print(json.dumps(res, indent=1))
