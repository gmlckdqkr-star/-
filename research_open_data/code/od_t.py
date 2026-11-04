"""OD-T: new free predictors -> NDX timing information gate (PRECOMMIT_OD1.md). <=2014 rows only."""
import sys, json, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
R = '/mnt/project-files/research/open_data/raw/'; END = pd.Timestamp('2014-12-31'); TR = 44
X = pd.ExcelFile(R + 'goyal_welch_zafirov_2024.xlsx')
def per_m(y, m): return pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
def series(raw, ends, lag_m):   # raw values with period-end dates -> availability dates
    avail = [e + pd.offsets.MonthEnd(lag_m) for e in ends]
    s = pd.Series(np.asarray(raw, float), index=pd.DatetimeIndex(avail)).dropna()
    return s[s.index <= END]
M = X.parse('Monthly'); M = M[M.yyyymm <= 201412]; me = [per_m(v // 100, v % 100) for v in M.yyyymm]
Q = X.parse('Quarterly'); Q = Q[Q.yyyyq <= 20144]; qe = [per_m(v // 10, (v % 10) * 3) for v in Q.yyyyq]
A = X.parse('Annual'); A = A[A.yyyy <= 2014]; ae = [per_m(v, 12) for v in A.yyyy]
P = {}
for c, sg, lag in [('ntis', -1, 1), ('lzrt', 1, 1), ('wtexas', -1, 1), ('skvw', -1, 1), ('tail', 1, 1), ('ndrbl', -1, 2),
                   ('disag', -1, 1), ('dfr', 1, 1), ('ltr', 1, 1), ('infl', -1, 2)]:
    P[c] = (series(M[c], me, lag), sg, 120)
for c, sg in [('i/k', -1), ('govik', 1)]: P[c] = (series(Q[c], qe, 4), sg, 40)
for c, sg in [('eqis', -1), ('accrul', 1), ('cfacc', 1), ('house', -1), ('gip', -1), ('gpce', -1)]: P[c] = (series(A[c], ae, 6), sg, 10)
ga = pd.read_csv(R + 'fred_GACDFSA066MSFRBPHI.csv', parse_dates=[0]).set_index('observation_date').iloc[:, 0]
no = pd.read_csv(R + 'fred_NOCDFSA066MSFRBPHI.csv', parse_dates=[0]).set_index('observation_date').iloc[:, 0]
P['phil_ga_chg3'] = (series(ga.diff(3).values, [d + pd.offsets.MonthEnd(0) for d in ga.index], 0), 1, 120)
P['phil_no_lvl'] = (series(no.values, [d + pd.offsets.MonthEnd(0) for d in no.index], 0), 1, 120)
C = pd.read_excel(R + 'CMO_monthly.xlsx', 'Monthly Prices', header=None)
hdr = [str(h) for h in C.iloc[4].tolist()]; rows = C.iloc[6:]; rows = rows[rows[0].map(str).str.match(r'^\d{4}M\d{2}$')]
ce = [per_m(int(s[:4]), int(s[5:])) for s in rows[0].map(str)]
cu = pd.to_numeric(rows[[i for i, h in enumerate(hdr) if h.strip().lower() == 'copper'][0]], errors='coerce').values
gd = pd.to_numeric(rows[[i for i, h in enumerate(hdr) if h.strip().lower() == 'gold'][0]], errors='coerce').values
cg = pd.Series(np.log(cu / gd)); P['copper_gold_chg6'] = (series(cg.diff(6).values, ce, 1), 1, 120)

def z(s, mn):
    mu = s.expanding().mean().shift(0); sd = s.expanding().std()
    zz = (s - mu) / sd; zz[np.arange(len(s)) < mn] = np.nan; return zz   # value at t uses data <= t only
res = {}; Z = {}
for k, (s, sg, mn) in P.items():
    zz = (z(s, mn) * sg).dropna(); Z[k] = zz
    for v, sig in [('V1', zz > 0), ('V2', ~(zz < -1))]:
        g = gate.test(sig, trials=TR, name=f'{k}_{v}', verbose=False)
        res[f'{k}_{v}'] = dict(first=str(zz.index[0].date()), frac_in=float(sig.mean()),
            **{e: (None if g[e] is None else {kk: round(g[e][kk], 4) for kk in ('hit', 'always_up', 'hit_deflated', 'n')}) for e in ('ndx_86_14', 'spx_55_85')}, verdict=g['verdict'])
mon = ['ntis', 'lzrt', 'wtexas', 'skvw', 'tail', 'ndrbl', 'disag', 'dfr', 'ltr', 'infl']
comb = pd.concat({k: Z[k] for k in mon}, axis=1).sort_index().ffill().mean(axis=1, skipna=True).dropna()
for v, sig in [('V1', comb > 0), ('V2', ~(comb < -1))]:
    g = gate.test(sig, trials=TR, verbose=False)
    res[f'combo_{v}'] = dict(first=str(comb.index[0].date()), frac_in=float(sig.mean()),
        **{e: {kk: round(g[e][kk], 4) for kk in ('hit', 'always_up', 'hit_deflated', 'n')} for e in ('ndx_86_14', 'spx_55_85')}, verdict=g['verdict'])
json.dump(res, open('/mnt/project-files/research/open_data/results/od_t.json', 'w'), indent=1, ensure_ascii=False)
print(f"{'name':22s} {'first':10s} in%  NDXhit (up) defl | SPXhit (up) defl | verdict")
for k, r in res.items():
    f = lambda e: '   -    ' if r[e] is None else f"{r[e]['hit']:.3f}({r[e]['always_up']:.3f}) {r[e]['hit_deflated']:.3f}"
    print(f"{k:22s} {r['first']} {r['frac_in']:.2f} {f('ndx_86_14')} | {f('spx_55_85')} | {r['verdict']}")
