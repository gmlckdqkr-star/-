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

v3 = v2 + `divy` (float32 [T, N]): the cash distribution paid on day t per share / the previous traded close, used by
lab ONLY to tax dividends (15.4% when paid, stocks.DIV_TAX); no score / filter / signal can read it.  Raw columns:
`close` is the traded close (NOT split-adjusted in the CRSP / Tiingo / WIKI rows, already split-adjusted in the Yahoo
rows), `dividends` is per share on day t's share basis, `stock_splits` is the factor on day t (0 / 1 = none), and the
source builds `adj_close` additively: adj_t / adj_{t-1} = k (close_t + div_t) / close_{t-1}, k = the split factor when
the close is on the pre-split basis at t-1, else 1 (109,193 of the 109,202 dividend rows <= 2014 match this to 1e-4).
  divy_t = div_t * k / close_{t-1}     (close_{t-1} = the name's previous source row, i.e. its previous traded close;
                                        k chosen on a split day by which basis reproduces adj, 1 on every other day)
  cap 1: divy_t <= max(0, adj_t / adj_{t-1} - k close_t / close_{t-1}) = the distribution the adjusted total return
         actually paid in that day (never tax a dividend the book's return did not receive)
  cap 2: div_t >= close_{t-1} on the source's own basis (a payout of more than the share was worth) -> 0
Every other distribution the source records is kept and taxed like a cash dividend, including stock dividends and
spin-offs it books as cash amounts (conservative: Korean tax treats foreign spin-off shares as deemed dividends).
Not in divy (so not taxed): 112 rows <= 2014 where adj implies a distribution > 0.2% that the dividends column does
not record (93 positive, summing to ~1.6% of the recorded distributions; e.g. a spin-off booked in adj only).
With a base panel (argv 4, e.g. the v2 file) every shared array is compared; when any differs, the base arrays are
kept and only divy comes from this download (reindexed onto the base dates / tickers), and META records the counts.

usage: python -I build_us_stocks.py <raw_dir> <out_dir> [tag] [base_npz]
  writes <out_dir>/sp500_le2014[_tag].npz.xz and META[_tag].json (lab: v3 = tag v3, base = the v2 file)
"""
import sys, os, re, json, hashlib, lzma, io
import numpy as np, pandas as pd
import pyarrow.parquet as pq

SEAL = pd.Timestamp('2014-12-31')
raw, out = sys.argv[1], sys.argv[2]
tag = f'_{sys.argv[3]}' if len(sys.argv) > 3 else ''
base = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


px = pq.read_table(os.path.join(raw, 'prices.parquet'),
                   columns=['date', 'ticker', 'close', 'volume', 'adj_close', 'source', 'dividends', 'stock_splits'],
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


def div_yield(px):
    """Per source row: (divy, info). See the module docstring for the rule (split basis k, caps 1 and 2)."""
    px = px.sort_values(['ticker', 'date'], kind='stable')
    g = px.groupby('ticker', sort=False)
    pc, pa = g.close.shift(1), g.adj_close.shift(1)
    dv = px.dividends.fillna(0.0)
    s = px.stock_splits.where((px.stock_splits > 0) & (px.stock_splits != 1), 1.0).fillna(1.0)
    ar = px.adj_close / pa
    prev = pc.notna() & (pc > 0) & pa.notna() & (pa > 0)
    on = (dv > 0) & prev
    eA = (ar - s * (px.close + dv) / pc).abs()                 # close on the pre-split basis at t-1 (CRSP-type rows)
    eB = (ar - (px.close + dv) / pc).abs()                     # close already split-adjusted (Yahoo rows)
    k = np.where(prev & (s != 1) & (eA < eB), s, 1.0)
    dys = np.where(on, dv * k / pc, 0.0)
    yall = np.where(prev, ar - k * px.close / pc, 0.0)         # adj/close implied distribution, every row (sanity)
    yadd = np.where(on, yall, 0.0)                             # distribution in the adjusted total return that day
    c2 = on & (dv >= pc)                                        # payout >= the previous close on its own basis
    y = np.where(c2, 0.0, np.minimum(dys, np.maximum(yadd, 0.0)))
    c1 = on & ~c2 & (y < dys - 1e-12)
    y = np.where(on, y, 0.0)
    rel = np.abs(dys - yadd) / np.maximum(dys, 1e-12)
    info = dict(rows=int(on.sum()), split_day_rows=int((on & (s != 1)).sum()), split_basis_rows=int((on & (k != 1)).sum()),
                no_prev_close=int(((dv > 0) & ~on).sum()), match_1e4=int((on & (rel <= 1e-4)).sum()),
                cap1_rows=int(c1.sum()), cap1_removed=float((dys - y)[c1].sum()), cap2_rows=int(c2.sum()),
                cap2_removed=float(dys[c2].sum()))
    big = px.loc[on & (y > 0.25), ['date']].assign(divy=y[on & (y > 0.25)])
    info['over_25pct'] = [dict(date=str(d.date()), divy=round(float(v), 4)) for d, v in zip(big.date, big.divy)]
    info['over_25pct'].sort(key=lambda r: -r['divy'])
    for c, m in (('cap1', c1), ('cap2', c2)):
        q = px.loc[m, ['date']]
        info[f'{c}_list'] = [dict(date=str(d.date()), recorded=round(float(a), 4), kept=round(float(b), 4))
                             for d, a, b in zip(q.date, dys[m], y[m])]
    nd = prev & ~on & (np.abs(yall) > 0.002)                  # adj implies a distribution the dividends column lacks
    info['implied_without_dividend'] = dict(rows=int(nd.sum()), positive=int((nd & (yall > 0)).sum()),
                                            sum_positive=float(yall[nd & (yall > 0)].sum()),
                                            sum_all_dividend_rows=float(y.sum()), note='not in divy (untaxed)')
    return pd.Series(y, index=px.index), pd.Series(yall, index=px.index), info


ren = neutral(tick, mi.groupby('ticker').start.min().to_dict())
assert len(set(ren.values())) == len(tick)
assert not [o for o in ren.values() if any(int(y) > 2014 for y in re.findall(r'(?:19|20)\d\d', o))]
px = px[px.ticker.isin(tick)]
divy_s, yadd_s, dinfo = div_yield(px)
dates = pd.DatetimeIndex(sorted(px.date.unique()))
ti = {t: i for i, t in enumerate(tick)}
T, N = len(dates), len(tick)
adj = np.full((T, N), np.nan, np.float32)
dv = np.full((T, N), np.nan, np.float32)
dvy = np.zeros((T, N), np.float32)
imp = np.zeros((T, N), np.float64)              # the adj/close implied distribution (sanity only, not written)
r = dates.get_indexer(px.date); c = px.ticker.map(ti).values
adj[r, c] = px.adj_close.values
dvv = (px.close * px.volume).values
dv[r, c] = np.where(np.isfinite(dvv) & (dvv > 0), dvv, np.nan)
dvy[r, c] = divy_s.reindex(px.index).values
imp[r, c] = yadd_s.reindex(px.index).values
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
tk = np.array([ren[t] for t in tick])

# ---- base panel (v2): every shared array must be identical; else keep the base arrays, take only divy
cmp = None
if base:
    zb = np.load(io.BytesIO(lzma.open(base).read()))
    Tb = int(zb['shape'][0])
    ub = lambda a: np.unpackbits(a, axis=0)[:Tb].astype(bool)
    same_grid = np.array_equal(zb['dates'], d0) and np.array_equal(np.asarray(zb['tickers']).astype(str), tk)
    cmp = dict(base=os.path.basename(base), dates_tickers_equal=bool(same_grid))
    if same_grid:
        for nm, a, b in (('adj', zb['adj'], adj), ('dvol', zb['dvol'], dv)):
            cmp[nm + '_diff'] = int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
        cmp['member_diff'] = int((ub(zb['member']) != mem).sum()); cmp['stale_diff'] = int((ub(zb['stale']) != stale).sum())
    ident = same_grid and all(v == 0 for kk, v in cmp.items() if kk.endswith('_diff'))
    cmp['identical'] = bool(ident)
    if not ident:                                # keep the base arrays; divy from this download on the base grid
        bd = pd.to_datetime(zb['dates'], unit='D'); bt = np.asarray(zb['tickers']).astype(str)
        D = pd.DataFrame(dvy, index=dates, columns=tk).reindex(index=bd, columns=bt).fillna(0.0)
        dvy = D.values.astype(np.float32)
        d0, tk = zb['dates'], bt
        adj, dv, mem, stale = zb['adj'], zb['dvol'], ub(zb['member']), ub(zb['stale'])
        dates, T, N = bd, Tb, len(bt)
        cmp['kept'] = 'base arrays (adj, dvol, member, stale, dates, tickers); divy from this download'

# ---- sanity: equal-weight member yield by year (members at t-1 with a price at t-1 and t, as _SP500EW)
fin = np.isfinite(adj) & (adj > 0)
M = np.zeros((T, N), bool)
M[1:] = mem[:-1] & fin[:-1] & fin[1:]
cnt = np.maximum(M.sum(1), 1)
ew_d = np.where(M, dvy, 0.0).sum(1) / cnt
ew_i = np.where(M & (np.abs(imp) <= 0.5), imp, 0.0).sum(1) / cnt if imp.shape == dvy.shape else 0.0 * ew_d   # |x| > 0.5: splice glitch
yrs = pd.DatetimeIndex(dates).year
by_year = {int(y): dict(divy=round(float(ew_d[yrs == y].sum()), 4), implied=round(float(ew_i[yrs == y].sum()), 4),
                        payers=round(float((np.where(M[yrs == y], dvy[yrs == y], 0) > 0).any(0).sum()
                                           / max(1, M[yrs == y].any(0).sum())), 3))
           for y in np.unique(yrs) if y >= 1970}          # members from 1970-01-02 (first PIT day)

buf = io.BytesIO()
np.savez(buf, dates=d0, tickers=tk, adj=adj, dvol=dv,
         member=np.packbits(mem, axis=0), stale=np.packbits(stale, axis=0), divy=dvy,
         shape=np.array([T, N]))
p = os.path.join(out, f'sp500_le2014{tag}.npz.xz')
with lzma.open(p, 'wb', preset=6) as f:
    f.write(buf.getvalue())
meta = dict(
    source='https://github.com/Johnbrick123/sp500-data releases/download/data (repo HEAD 981c7d25, files Last-Modified 2026-11-03 04:10 GMT)',
    licence='none published; personal research only, do not republish',
    raw_sha256={f: sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw)) if not f.endswith('.hdr')},
    built=pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M UTC'),
    seal='2014-12-31 (no later rows; membership ends after 2014 cleared; delisting suffixes after 2014 dropped, '
         'shared bare symbols ordered by first membership start)',
    survivorship='delisted and removed S&P 500 members included (point-in-time membership intervals)',
    label='ACTUAL (CRSP/Yahoo/Tiingo/WIKI splice by the source; 1996-2000 crsp-patch rows disputed ~0.9% of rows)',
    T=T, N=N, first=str(pd.DatetimeIndex(dates)[0].date()), last=str(pd.DatetimeIndex(dates)[-1].date()),
    member_days=int(mem.sum()), member_days_with_price=int((mem & np.isfinite(adj)).sum()),
    exit_gaps=gaps, base_compare=cmp,
    divy=dict(rule='divy_t = div_t * k / close_{t-1} (k = split factor when the raw close is on the pre-split basis at '
                   't-1, chosen by which basis reproduces adj; 1 otherwise); cap 1: <= max(0, adj_t/adj_{t-1} - k '
                   'close_t/close_{t-1}) (never more than the adjusted total return paid in); cap 2: div_t >= '
                   'close_{t-1} -> 0. Stock dividends / spin-offs the source books as cash are kept (taxed as cash, '
                   'conservative). lab use: dividend tax only (stocks.DIV_TAX), unreadable by score / filter / signals.',
              **dinfo, ew_member_yield_by_year=by_year),
    out_sha256=sha(p))
json.dump(meta, open(os.path.join(out, f'META{tag}.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in meta.items() if k not in ('exit_gaps', 'raw_sha256', 'divy')}, indent=1))
print(json.dumps({k: v for k, v in meta['divy'].items() if k not in ('ew_member_yield_by_year', 'cap1_list')}, indent=1))
print(' '.join(f"{y}:{v['divy']:.3f}/{v['implied']:.3f}" for y, v in by_year.items()))
