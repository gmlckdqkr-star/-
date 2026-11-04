"""GT2: clone giants' 13F holdings (PRECOMMIT_GT2.md). Daily engine = gteng.run on trading days."""
import sys, json, io, lzma, re, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/giant_trend/code'); import gteng as E
R2 = '/mnt/project-files/research/giant_trend/results2/'
NB = int(sys.argv[1]) if len(sys.argv) > 1 else 200
z = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz').read()), allow_pickle=True)
dates = pd.to_datetime(z['dates'], unit='D'); T = len(dates); tick = z['tickers']; N = len(tick)
adj = z['adj'].astype(np.float64); divy = z['divy'].astype(np.float64)
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
assert dates[-1] <= pd.Timestamp('2014-12-31')
# daily returns with lab-style delisting rule
ret = np.zeros((T, N)); lastp = np.full(N, -1)
for j in range(N):
    p = adj[:, j]; ok = np.where(np.isfinite(p))[0]
    if len(ok) < 2: continue
    pf = pd.Series(p).ffill().values; r = np.zeros(T); r[1:] = pf[1:] / pf[:-1] - 1; r[~np.isfinite(r)] = 0
    r[:ok[0] + 1] = 0; last = ok[-1]; lastp[j] = last
    if last < T - 6:   # delisted before the end
        r250 = pf[last] / pf[max(last - 250, ok[0])] - 1
        r[last + 1] = -0.5 if r250 < -0.3 else 0.0; r[last + 2:] = 0.0
    ret[:, j] = r - 0.154 * np.nan_to_num(divy[:, j])          # dividend withholding (adj includes dividends)
base = np.array([re.sub(r'[^A-Z0-9]', '', re.sub(r'-\d{6}$', '', t).split('_')[0].upper()) for t in tick])
# T-bill daily
tb = pd.read_csv('/mnt/project-files/research/data/deep_history/clean/TBILL_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
rf = (tb['rate_known_pct'].reindex(dates).ffill() / 100 / 252).values
cash = np.maximum(rf - 0.02 / 252, 0) * 0.846
E.IS_DEC = np.r_[dates.year[1:] != dates.year[:-1], True]
P = {1: {j: ret[:, j] for j in range(N)}}; P[1]['CASH'] = cash
for L in (2, 3): P[L] = P[1]
E.FEE = 0.0
# ---- holdings -> panel ids --------------------------------------------------------------
H = json.load(open(R2 + 'holdings.json')); fm = json.load(open(R2 + 'figi_map.json'))
def day_of(s): return int(np.searchsorted(dates, pd.Timestamp(s)))
CM = {c: int(j) for c, j in json.load(open(R2 + 'cusip_map.json')).items()}
def to_ids(hold, d):
    out = {}; tot = 0.0; got = 0.0
    for c, (v, nm, *_) in hold.items():
        tot += v; j = CM.get(c)
        if j is None or not mem[d, j] or not np.isfinite(adj[d, j]): continue
        out[j] = out.get(j, 0) + v; got += v
    return out, (got / tot if tot else 0)
F = []   # filings with decision day
for h in H:
    d = day_of(h['filed']) + 2
    if d >= T: continue
    ids, cov = to_ids(h['hold'], d); F.append(dict(g=h['giant'], d=d, ids=ids, cov=cov, filed=h['filed']))
F.sort(key=lambda x: x['d'])
cov = pd.DataFrame([(f['g'], f['cov']) for f in F], columns=['g', 'cov']).groupby('g')['cov'].median().round(3).to_dict()
print('coverage median by giant', cov, flush=True)
def cap(w, c=0.25):
    w = {k: v for k, v in w.items() if v > 0 and np.isfinite(v)}
    if not w: return {'CASH': 1.0}
    if len(w) * c < 1: c = 1.0 / len(w)   # too few names for the cap: equal weight
    for _ in range(20):
        s = sum(w.values()); w = {k: v / s for k, v in w.items()}
        over = [k for k, v in w.items() if v > c + 1e-12]
        if not over: break
        ex = sum(w[k] - c for k in over); rest = [k for k in w if k not in over]; rs = sum(w[k] for k in rest)
        for k in over: w[k] = c
        for k in rest: w[k] += ex * w[k] / rs if rs else 0
    return w
def mom_ok(j, d):
    a, b = d - 252, d - 21
    return a >= 0 and np.isfinite(adj[a, j]) and np.isfinite(adj[b, j]) and adj[b, j] / adj[a, j] - 1 > 0
GIANTS = sorted({f['g'] for f in F})
cur = {}; prev = {}; newbuys = []   # newbuys: (giant, id, until_day)
DEC = {k: [None] * T for k in ['C1_' + g for g in GIANTS] + ['C1_EW', 'C2', 'C3', 'C4', 'C2T', 'C3T', 'C4T', 'EW']}
for f in F:
    d = f['d']; g = f['g']
    if f['ids']:
        prev[g] = cur.get(g, {}); cur[g] = dict(f['ids'], _d=d)
        for j in f['ids']:
            if prev[g] and j not in prev[g]: newbuys.append((g, j, d + 252))
    live = {gg: {k: v for k, v in w.items() if k != '_d'} for gg, w in cur.items() if d - w['_d'] <= 200}
    if g in live: DEC['C1_' + g][d] = ('w', cap(live[g]))
    if live:
        agg = {}
        for gg, w in live.items():
            for k, v in cap(w).items(): agg[k] = agg.get(k, 0) + v / len(live)
        DEC['C1_EW'][d] = ('w', agg)
        cnt = {}
        for w in live.values():
            for k in w: cnt[k] = cnt.get(k, 0) + 1
        c2 = [k for k, n in cnt.items() if n >= 2]
        c3 = sorted({k for w in live.values() for k in sorted(w, key=w.get, reverse=True)[:5]})
        c4 = sorted({j for gg, j, u in newbuys if u > d})
        for nm, s in (('C2', c2), ('C3', c3), ('C4', c4)):
            DEC[nm][d] = ('w', {k: 1 / len(s) for k in s}) if s else ('w', {'CASH': 1.0})
            st = [k for k in s if mom_ok(k, d)]
            DEC[nm + 'T'][d] = ('w', {k: 1 / len(st) for k in st}) if st else ('w', {'CASH': 1.0})
# EW baseline: rebalance at each quarter's first trading day
for d in range(1, T):
    if dates[d].quarter != dates[d - 1].quarter and dates[d] >= pd.Timestamp('1999-05-01'):
        ids = [j for j in np.where(mem[d])[0] if np.isfinite(adj[d, j])]; DEC['EW'][d] = ('w', {j: 1 / len(ids) for j in ids})
ones = np.ones(T, int)
def span(a, b):
    i0 = int(np.searchsorted(dates, pd.Timestamp(a))); i1 = int(np.searchsorted(dates, pd.Timestamp(b), side='right')) - 1
    return list(range(i0 - 1, i1 + 1))
def st(w, pre, mm):
    yrs = (len(w) - 1) / 252; cg = w[-1] ** (1 / yrs) - 1; ex = pre - rf[mm[1:]]
    pk = np.maximum.accumulate(w); return dict(cagr=round(float(cg), 4), sharpe=round(float(ex.mean() / ex.std() * np.sqrt(252)), 3), mdd=round(float((w / pk - 1).min()), 3))
ERAS = [('FULL', '1999-05-20', '2014-12-31'), ('H1', '1999-05-20', '2006-12-31'), ('H2', '2007-01-01', '2014-12-31')]
rng = np.random.default_rng(20261104); b0 = int(np.searchsorted(dates, pd.Timestamp('1999-05-20'))); PATHS = []
for _ in range(NB):
    s0 = rng.integers(b0 + 1, T - 252, size=30); m = [int(s0[0]) - 1]
    for s in s0: m += list(range(int(s), int(s) + 252))
    PATHS.append(m)
out = {'coverage': cov, 'n_filings': len(F)}; LW = {}
for nm, dec in DEC.items():
    if all(x is None for x in dec): continue
    row = {}
    for tag, a, b in ERAS:
        mm = span(a, b); w, pre = E.run(dec, ones, P, mm); row[tag] = st(w, pre, mm)
    lw = []; cg = []
    for m in PATHS:
        w, _ = E.run(dec, ones, P, m); cg.append(w[-1] ** (1 / 30) - 1 if w[-1] > 0 else -1); lw.append(np.log(max(w[-1], 1e-12)))
    LW[nm] = np.array(lw); row['BOOT'] = dict(med=round(float(np.median(cg)), 4), p10=round(float(np.percentile(cg, 10)), 4))
    out[nm] = row; print(nm, row, flush=True)
for nm in LW:
    d = (LW[nm] - LW['EW']) / 30; out[nm]['BOOT']['d_vs_EW'] = round(float(np.median(d)), 4); out[nm]['BOOT']['win'] = round(float((d > 0).mean()), 3)
json.dump(out, open(R2 + 'gt2_main.json', 'w'), indent=1)
