"""Build the sealed <=2014 S&P 500 single-stock panel for lab.

Source: github.com/Johnbrick123/sp500-data release 'data' (no licence file;
personal research only, never republish).  Run with a python that has
pyarrow.  Nothing dated after 2014-12-31 is written; membership ends after
2014 are cleared (set to 'open'), and a delisting suffix dated after 2014
(the source writes AET-201811) is dropped from the ticker (AET), so the
panel holds no post-2014 dates.  When names then share a bare symbol, the
one with the earliest first membership start (a <= 2014 fact) keeps it and
the others get _2, _3 in that order: the suffix does not mark WHICH name was
delisted after 2014.  Limit (the strings are not point in time): symbols are
the source's last-known ones, so a rename after 2014 shows the new symbol,
and an X / X_2 pair (8 in v2) exists only because one of the two was
delisted after 2014 (in three pairs both names are members at the same
time).  lab never selects by symbol and prints
point-in-time ids instead (stocks.Panel.label).

usage: python -I build_us_stocks.py <raw_dir> <out_dir> [tag]
  writes <out_dir>/sp500_le2014[_tag].npz.xz and META[_tag].json (lab: v2 = tag v2)
"""
import sys, os, re, json, hashlib, lzma, io
import numpy as np, pandas as pd
import pyarrow.parquet as pq

SEAL = pd.Timestamp('2014-12-31')
raw, out = sys.argv[1], sys.argv[2]
tag = f'_{sys.argv[3]}' if len(sys.argv) > 3 else ''
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


def neutral(names, first_member):
    """Output symbol per source ticker: a delisting suffix after 2014 (-YYYYMM > 201412) is a post-2014 fact and is
    dropped. Names that then share one bare symbol are ordered by first membership start (<= 2014): the first keeps
    the bare symbol, the others get _2, _3 ... (the order encodes nothing after 2014; ties are refused)."""
    post = lambda t: len(t) > 7 and t[-7] == '-' and t[-6:].isdigit() and t[-6:] > '201412'
    groups = {}
    for t in names:
        groups.setdefault(t[:-7] if post(t) else t, []).append(t)
    out, used = {}, set(groups)
    for b, ts in groups.items():
        ts = sorted(ts, key=lambda t: first_member[t])
        assert len({first_member[t] for t in ts}) == len(ts), f'tie in first membership for {ts}'
        out[ts[0]] = b
        for t in ts[1:]:
            k = 2
            while f'{b}_{k}' in used:
                k += 1
            out[t] = f'{b}_{k}'; used.add(out[t])
    return out


ren = neutral(tick, mi.groupby('ticker').start.min().to_dict())
assert len(set(ren.values())) == len(tick)
assert not [o for o in ren.values() if any(int(y) > 2014 for y in re.findall(r'(?:19|20)\d\d', o))]
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
gaps = [dict(ticker=ren[g.ticker], last_trade=str(g.last_trade.date()), next_trade=str(g.next_trade.date()),
             change=float(g.change)) for g in eg.itertuples() if g.ticker in ti]
d0 = np.int64(dates.values.astype('datetime64[D]').astype(np.int64))
buf = io.BytesIO()
np.savez(buf, dates=d0, tickers=np.array([ren[t] for t in tick]), adj=adj, dvol=dv,
         member=np.packbits(mem, axis=0), stale=np.packbits(stale, axis=0),
         shape=np.array([T, N]))
p = os.path.join(out, f'sp500_le2014{tag}.npz.xz')
with lzma.open(p, 'wb', preset=6) as f:
    f.write(buf.getvalue())
meta = dict(
    source='https://github.com/Johnbrick123/sp500-data releases/download/data (repo HEAD 981c7d25, files Last-Modified 2026-11-03 04:10 GMT)',
    licence='none published; personal research only, do not republish',
    raw_sha256={f: sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw)) if not f.endswith('.hdr')},
    seal='2014-12-31 (no later rows; membership ends after 2014 cleared; delisting suffixes after 2014 dropped, '
         'shared bare symbols ordered by first membership start)',
    survivorship='delisted and removed S&P 500 members included (point-in-time membership intervals)',
    label='ACTUAL (CRSP/Yahoo/Tiingo/WIKI splice by the source; 1996-2000 crsp-patch rows disputed ~0.9% of rows)',
    T=T, N=N, first=str(dates[0].date()), last=str(dates[-1].date()),
    member_days=int(mem.sum()), member_days_with_price=int((mem & np.isfinite(adj)).sum()),
    exit_gaps=gaps, out_sha256=sha(p))
json.dump(meta, open(os.path.join(out, f'META{tag}.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in meta.items() if k not in ('exit_gaps', 'raw_sha256')}, indent=1))
