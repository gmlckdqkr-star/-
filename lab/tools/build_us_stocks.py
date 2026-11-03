"""Build the sealed <=2014 S&P 500 single-stock panel for lab.

Source: github.com/Johnbrick123/sp500-data release 'data' (no licence file;
personal research only, never republish).  Run with a python that has
pyarrow.  Nothing dated after 2014-12-31 is written; membership ends after
2014 are cleared (set to 'open'), so the panel holds no post-2014 facts.

usage: python -I build_us_stocks.py <raw_dir> <out_dir>
"""
import sys, os, json, hashlib, lzma, io
import numpy as np, pandas as pd
import pyarrow.parquet as pq

SEAL = pd.Timestamp('2014-12-31')
raw, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

px = pq.read_table(os.path.join(raw, 'prices.parquet'),
                   columns=['date', 'ticker', 'close', 'volume', 'adj_close', 'source'],
                   filters=[('date', '<=', SEAL)]).to_pandas()
assert px.date.max() <= SEAL
px = px[px.date >= '1968-01-01']
mi = pq.read_table(os.path.join(raw, 'membership_intervals.parquet')).to_pandas()
mi = mi[mi.start <= SEAL].copy()
mi.loc[mi.end > SEAL, 'end'] = pd.NaT            # post-2014 exits are not disclosed
ntd = pd.read_csv(os.path.join(raw, 'no_trade_days.csv'), parse_dates=['date'])
ntd = ntd[ntd.date <= SEAL]
eg = pd.read_csv(os.path.join(raw, 'exit_gaps.csv'), parse_dates=['removed', 'last_member_day', 'last_trade', 'next_trade'])
eg = eg[eg.removed <= SEAL]
eg = eg[eg.next_trade <= SEAL]                  # a gap that closes after 2014 is not used

tick = sorted(set(mi.ticker))                    # every name that was ever a member <=2014
px = px[px.ticker.isin(tick)]
dates = pd.DatetimeIndex(sorted(px.date.unique()))
ti = {t: i for i, t in enumerate(tick)}
T, N = len(dates), len(tick)
adj = np.full((T, N), np.nan, np.float32)
dv = np.full((T, N), np.nan, np.float32)
r = dates.get_indexer(px.date); c = px.ticker.map(ti).values
adj[r, c] = px.adj_close.values
dvv = (px.close * px.volume).values
dv[r, c] = np.where(np.isfinite(dvv) & (dvv > 0), dvv, np.nan)
mem = np.zeros((T, N), bool)
for t, s, e in mi[['ticker', 'start', 'end']].itertuples(index=False):
    a = dates.searchsorted(s); b = T if pd.isna(e) else dates.searchsorted(e)
    mem[a:b, ti[t]] = True
stale = np.zeros((T, N), bool)
k = ntd[ntd.ticker.isin(ti)]
rr = dates.get_indexer(k.date); ok = rr >= 0
stale[rr[ok], k.ticker[ok].map(ti).values] = True
# exit gaps: prices missing between last_trade and next_trade while the
# position cannot be sold; the builder keeps them NaN and records the gap.
gaps = [dict(ticker=g.ticker, last_trade=str(g.last_trade.date()), next_trade=str(g.next_trade.date()),
             change=float(g.change)) for g in eg.itertuples() if g.ticker in ti]
d0 = np.int64(dates.values.astype('datetime64[D]').astype(np.int64))
buf = io.BytesIO()
np.savez(buf, dates=d0, tickers=np.array(tick), adj=adj, dvol=dv,
         member=np.packbits(mem, axis=0), stale=np.packbits(stale, axis=0),
         shape=np.array([T, N]))
p = os.path.join(out, 'sp500_le2014.npz.xz')
with lzma.open(p, 'wb', preset=6) as f:
    f.write(buf.getvalue())
meta = dict(
    source='https://github.com/Johnbrick123/sp500-data releases/download/data (repo HEAD 981c7d25, files Last-Modified 2026-11-03 04:10 GMT)',
    licence='none published; personal research only, do not republish',
    raw_sha256={f: sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw)) if not f.endswith('.hdr')},
    seal='2014-12-31 (no later rows; membership ends after 2014 cleared)',
    survivorship='delisted and removed S&P 500 members included (point-in-time membership intervals)',
    label='ACTUAL (CRSP/Yahoo/Tiingo/WIKI splice by the source; 1996-2000 crsp-patch rows disputed ~0.9% of rows)',
    T=T, N=N, first=str(dates[0].date()), last=str(dates[-1].date()),
    member_days=int(mem.sum()), member_days_with_price=int((mem & np.isfinite(adj)).sum()),
    exit_gaps=gaps, out_sha256=sha(p))
json.dump(meta, open(os.path.join(out, 'META.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in meta.items() if k not in ('exit_gaps', 'raw_sha256')}, indent=1))
