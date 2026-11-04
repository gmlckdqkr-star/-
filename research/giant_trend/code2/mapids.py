"""CUSIP -> panel id with price-consistency validation.
Candidates: FIGI ticker (and optional name-fallback ticker file) -> panel symbols with the same base ticker.
Validation: implied 13F price (value/shares) vs panel adjusted close at the report date; consecutive-filing changes of
log(adj / implied) must stay within 0.2 for >= 75% of pairs (splits and dividends move it slowly or by a split step).
A candidate passes if it is the only panel id whose check passes. Writes results2/cusip_map.json."""
import json, io, lzma, re, os, numpy as np, pandas as pd
R2 = '/mnt/project-files/research/giant_trend/results2/'
z = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz').read()), allow_pickle=True)
dates = pd.to_datetime(z['dates'], unit='D'); tick = z['tickers']; adj = z['adj'].astype(float)
mem = np.unpackbits(z['member'], axis=0)[:len(dates)].astype(bool)
base = np.array([re.sub(r'[^A-Z0-9]', '', re.sub(r'-\d{6}$', '', t).split('_')[0].upper()) for t in tick])
H = json.load(open(R2 + 'holdings.json')); fm = json.load(open(R2 + 'figi_map.json'))
nf = json.load(open(R2 + 'name_fallback.json')) if os.path.exists(R2 + 'name_fallback.json') else {}
ALIAS = {}
for line in open(R2 + 'panel_renames.csv').read().split()[1:]:
    o, n = line.split(','); ALIAS[re.sub(r'[^A-Z0-9]', '', o)] = re.sub(r'[^A-Z0-9]', '', n)
nf2 = json.load(open(R2 + 'name_fallback2.json')) if os.path.exists(R2 + 'name_fallback2.json') else {}
obs = {}
for h in H:
    if not h['period']: continue
    d = int(np.searchsorted(dates, pd.Timestamp(h['period']), side='right')) - 1
    for c, (v, nm, sh) in h['hold'].items():
        if v > 0 and sh > 0: obs.setdefault(c, []).append((h['giant'], d, v / sh))
def check(j, ob):
    dd = []; n = 0
    for g in {x[0] for x in ob}:
        r = []
        for _, d, p in sorted(x for x in set(ob) if x[0] == g):
            a = adj[d, j]
            if np.isfinite(a) and a > 0: r.append(np.log(a / p))
        n += len(r); dd += list(np.abs(np.diff(r)))
    if not dd: return n == 1, n
    return (np.array(dd) < 0.2).mean() >= 0.75, n
out = {}; stat = {'figi': 0, 'name': 0, 'fail': 0, 'nocand': 0}
for c in obs:
    tks = []
    if fm.get(c) and fm[c][0]: tks.append(('figi', fm[c][0]))
    if c in nf and nf[c]: tks.append(('name', nf[c]))
    if c in nf2 and nf2[c]: tks.append(('name', nf2[c]))
    ok = []
    for src, tk in tks:
        b = re.sub(r'[^A-Z0-9]', '', tk.upper()); b = ALIAS.get(b, b)
        for j in np.where(base == b)[0]:
            if not mem[[d for _, d, _ in obs[c]], j].any(): continue
            good, n = check(j, obs[c])
            if good: ok.append((src, int(j), n))
        if ok: break
    if not tks: stat['nocand'] += 1
    elif len({j for _, j, _ in ok}) == 1: out[c] = ok[0][1]; stat[ok[0][0]] += 1
    else: stat['fail'] += 1
json.dump({c: int(j) for c, j in out.items()}, open(R2 + 'cusip_map.json', 'w'))
print(stat, len(out))
