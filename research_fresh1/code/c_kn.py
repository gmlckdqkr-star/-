"""FRESH1 C-KN: Korean night hold, exactly as PREREG_C1_FRESH1.md. Data <= 2014 (already cut). All rows reported."""
import json, numpy as np, pandas as pd
D = pd.read_csv('/mnt/project-files/research/onf1/data_cut/kr_le2014.csv', index_col=0, parse_dates=True)
assert D.index.max() <= pd.Timestamp('2014-12-31')
COST = dict(LOW=0.0003, DESIGN=0.00046, STD=0.0026, DESIGN2x=0.00092)
OUT = {}


def nw_t(x, lags=5):
    x = np.asarray(x, float); n = len(x); m = x.mean(); e = x - m
    v = (e * e).sum() / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * (e[L:] * e[:-L]).sum() / n
    return float(m / np.sqrt(v / n))


def cagr(r, idx):
    yrs = (idx[-1] - idx[0]).days / 365.25
    return float(np.prod(1 + r) ** (1 / yrs) - 1)


def mdd(r):
    e = np.cumprod(1 + r); return float((e / np.maximum.accumulate(e) - 1).min())


k = D[['k_n', 'k_d', 'k_close']].dropna()
ln, ld = np.log1p(k['k_n']), np.log1p(k['k_d'])
OUT['G1'] = dict(mean_night_bp=float(ln.mean() * 1e4), mean_day_bp=float(ld.mean() * 1e4), ann_night=float(ln.mean() * 247), ann_day=float(ld.mean() * 247),
                 nw_t_diff=nw_t((ln - ld).values), nw_t_night=nw_t(ln.values), n=len(k), start=str(k.index[0].date()), end=str(k.index[-1].date()),
                 night_vol=float(ln.std() * np.sqrt(247)), day_vol=float(ld.std() * np.sqrt(247)))

# synthetic 2x night-only (2007-2014) and buy-and-hold 2x of the same series
syn_n = 2 * k['k_n'].values - 0.0064 / 252
syn_bh = (1 + 2 * k['k_n'].values - 0.0064 / 252) * (1 + 2 * k['k_d'].values) - 1      # 2x held night and day (daily reset at each leg)
# actual 2x ETF (2010-02-23..)
lv = D[['lev_n', 'lev_d']].dropna()
act_n = lv['lev_n'].values; act_bh = (1 + lv['lev_n'].values) * (1 + lv['lev_d'].values) - 1

G2 = {}
for nm, rn, bh, idx in (('actual_lev_2010_14', act_n, act_bh, lv.index), ('synthetic_2x_2007_14', syn_n, syn_bh, k.index)):
    o = dict(gross=cagr(rn, idx), buy_hold=cagr(bh, idx), n=len(rn), mean_night_bp=float(rn.mean() * 1e4), mdd_gross=mdd(rn))
    for cn, c in COST.items():
        o['net_' + cn] = cagr(rn - c, idx); o['mdd_' + cn] = mdd(rn - c)
    G2[nm] = o
OUT['G2'] = G2

# G3: calendar years, synthetic 2x night-only net at DESIGN cost
yr = {}
for y, g in pd.Series(syn_n - COST['DESIGN'], index=k.index).groupby(k.index.year):
    yr[int(y)] = float(np.prod(1 + g.values) - 1)
OUT['G3'] = dict(by_year=yr, positive=int(sum(v > 0 for v in yr.values())), years=len(yr))
yr1 = {}
for y, g in k['k_n'].groupby(k.index.year): yr1[int(y)] = dict(night_1x=float(np.prod(1 + g.values) - 1), day_1x=float(np.prod(1 + k['k_d'][g.index].values) - 1))
OUT['by_year_1x_gross'] = yr1

# halves
for nm, a, b in (('2007_10', '2007-01-01', '2010-12-31'), ('2011_14', '2011-01-01', '2014-12-31')):
    s = k.loc[a:b]
    OUT['half_' + nm] = dict(night_1x_ann=float(np.log1p(s['k_n']).mean() * 247), day_1x_ann=float(np.log1p(s['k_d']).mean() * 247),
                             nw_t_diff=nw_t((np.log1p(s['k_n']) - np.log1p(s['k_d'])).values),
                             syn2x_net_DESIGN=cagr(2 * s['k_n'].values - 0.0064 / 252 - COST['DESIGN'], s.index))

# reported, not selectable: P1 trend filter (close above 200-day mean, 1-day lag), P2 3x futures proxy at 0.02% per night
sma = k['k_close'].rolling(200).mean(); on = (k['k_close'] > sma).shift(1, fill_value=False).to_numpy(dtype=bool)   # decided with close t-1 for the night into t
p1 = np.where(on, syn_n - COST['DESIGN'], 0.0); v = sma.notna().shift(1, fill_value=False).to_numpy(dtype=bool)
OUT['P1_trend_filter'] = dict(net_DESIGN=cagr(p1[v], k.index[v]), same_window_P0=cagr((syn_n - COST['DESIGN'])[v], k.index[v]), share_on=float(on[v].mean()))
f = D['kr_n'].dropna()
OUT['P2_futures3x_proxy'] = dict(net=cagr(3 * f.values - 0.0002, f.index), gross_1x_ann=float(np.log1p(f).mean() * 247), mdd=mdd(3 * f.values - 0.0002),
                                 start=str(f.index[0].date()), n=len(f), note='before 11% tax; proxy = (lev_n - inv_n)/3')

# data diagnostics found after the run (reported, change no gate): coverage by year and 1x-fund vs actual 2x-fund night returns
cm = D[['lev_n', 'lev_d', 'k_n', 'k_d', 'inv_n']].dropna()
OUT['data_note'] = dict(
    k_n_rows_by_year={int(y): int(n) for y, n in D['k_n'].notna().groupby(D.index.year).sum().items()},
    common_sample_n=len(cm), night_mean_bp_actual_2x=float(cm['lev_n'].mean() * 1e4), night_mean_bp_2x_of_1x_fund=float(2 * cm['k_n'].mean() * 1e4),
    corr=float(np.corrcoef(cm['lev_n'], 2 * cm['k_n'])[0, 1]),
    by_year={int(y): dict(actual_2x_night=float(np.prod(1 + g['lev_n']) - 1), two_x_of_1x_night=float(np.prod(1 + 2 * g['k_n']) - 1),
                          minus_inverse_night=float(np.prod(1 - g['inv_n']) - 1)) for y, g in cm.groupby(cm.index.year)},
    note='KODEX 200 open prices exist only for 8 days of 2007, none of 2008, from 2009-04 on. In the common sample the actual 2x fund earns '
         'about half the night return implied by the 1x fund open prices, so the 1x-fund night series overstates the tradable effect. '
         'The actual 2x fund (lev_n) is the binding series.')

g1 = OUT['G1']['nw_t_diff'] >= 3
g2 = all(G2[n]['net_DESIGN'] >= 0.08 and G2[n]['net_DESIGN'] >= G2[n]['buy_hold'] for n in G2)
g3 = OUT['G3']['positive'] >= 6
st = all(G2[n]['net_DESIGN2x'] > 0 for n in G2)
OUT['verdict'] = dict(G1=bool(g1), G2=bool(g2), G3=bool(g3), stress=bool(st), PASS=bool(g1 and g2 and g3 and st))
json.dump(OUT, open('/mnt/project-files/research/fresh1/results/c_kn.json', 'w'), indent=1)
print(json.dumps(OUT, indent=1))
