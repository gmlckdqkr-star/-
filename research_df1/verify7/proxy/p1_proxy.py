"""verify7/proxy: audit of df7.trend_by_date (look-ahead, inputs, stats, decomposition, AQR comparison, fee estimate). <=2014 only.
Run: mkdir -p /tmp/df7v_proxy && cd /tmp/df7v_proxy && export NUMBA_CACHE_DIR=/tmp/df7v_proxy/nb && python3 -B /mnt/project-files/research/df1/verify7/proxy/p1_proxy.py"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D, df5data as DD, df5lib as L
OUT = '/tmp/df7v_proxy/proxy_audit.json'
END = pd.Timestamp('2014-12-31')
R = {}
MK = ['SPX', 'LTT', 'GOLD', 'USD', 'DEVX']

# ---------------- 0. inputs
X, S = L._src('1984-01-03', '2014-12-31', 'SPX'); idx = S.index; rf = S['M_rf'].fillna(0.0)
assert idx.max() <= END
src = DD.src_series()
R['inputs'] = {k: dict(start=str(src[k].index.min().date()), end=str(src[k].index.max().date()), n=int(len(src[k])), nan=int(src[k].isna().sum()))
               for k in ('LTT', 'GOLD', 'USD', 'DEVX')}
R['inputs']['calendar'] = dict(start=str(idx.min().date()), end=str(idx.max().date()), n=len(idx))
for k in ('LTT', 'GOLD', 'USD', 'DEVX'):
    s = src[k]; rr = s.reindex(idx); first = s.index.min()
    R['inputs'][k]['nan_on_cal_after_start'] = int(rr[rr.index >= first].isna().sum())
    R['inputs'][k]['src_days_off_cal_after_1984'] = int((~s[s.index >= idx.min()].index.isin(idx)).sum())
s = S['SPX']; R['inputs']['SPX_cagr_1984_2014'] = float(np.prod(1 + s) ** (252 / len(s)) - 1)

# ---------------- 1. own re-implementation, exact match, perturbation look-ahead test
def build_ex(idx, S, src):
    rf = S['M_rf'].fillna(0.0); ex = pd.DataFrame(index=idx); ex['SPX'] = S['SPX'] - rf
    for k in ('LTT', 'GOLD', 'USD', 'DEVX'):
        s = src[k].reindex(idx); first = src[k].index.min(); s[s.index >= first] = s[s.index >= first].fillna(0.0); ex[k] = s - rf
    return ex

def trend(ex, V=0.12, lbs=(63, 126, 252), volw=60, reb=5, cap=3.0):
    lg = np.log1p(ex); cum = lg.cumsum()
    sig = sum(np.sign(cum - cum.shift(L_)) for L_ in lbs) / len(lbs)
    vol = ex.rolling(volw).std() * np.sqrt(252)
    ok = cum.shift(max(lbs)).notna() & vol.notna(); N = ok.sum(axis=1).replace(0, np.nan)
    w = (sig / vol).mul(V / np.sqrt(N), axis=0).clip(-cap, cap).where(ok, 0.0).shift(1)
    keep = np.arange(len(ex)) % reb == 0
    w = w.where(pd.Series(keep, index=ex.index), np.nan).ffill().fillna(0.0)
    return w, (w * ex.fillna(0.0)).sum(axis=1)

d = D.trend_by_date(); ex = build_ex(idx, S, src); w, tr = trend(ex)
R['reimpl'] = dict(max_abs_diff_tr=float((tr - d['tr']).abs().max()), max_abs_diff_w=float((w - d['w']).abs().max().max()))
lk = []
rng = np.random.default_rng(1)
for t0 in sorted(rng.choice(np.arange(400, len(idx) - 10), 12, replace=False)):
    ex2 = ex.copy(); ex2.iloc[t0:, :] = ex2.iloc[t0:, :] * -3.0 + 0.05       # change everything from day t0 on
    w2, _ = trend(ex2)
    lk.append(dict(t0=str(idx[t0].date()), w_diff_upto_t0=float((w2.iloc[:t0 + 1] - w.iloc[:t0 + 1]).abs().max().max()),
                   w_diff_after=float((w2.iloc[t0 + 1:t0 + 8] - w.iloc[t0 + 1:t0 + 8]).abs().max().max())))
R['lookahead_perturb'] = lk
# position change days, first active day per market
chg = (w.diff().abs().sum(axis=1) > 0)
R['rebalance'] = dict(n_change_days=int(chg.sum()), mean_gap_days=float(np.diff(np.where(chg.values)[0]).mean()),
                      first_nonzero={k: str(w[k][w[k] != 0].index.min().date()) for k in MK})
t = w.index >= '1986-01-01'
R['nmarkets_1986'] = {str(y): float((w[t] != 0).sum(axis=1).groupby(w[t].index.year).mean()[y]) for y in (1986, 1990, 1991, 1992, 2000, 2014)}
R['cap_binding_frac'] = {k: float((d['w'][k][t].abs() >= 2.999).mean()) for k in MK}
R['avg_abs_w_1986_2014'] = {k: float(w[k][t].abs().mean()) for k in MK}
R['frac_long_1986_2014'] = {k: float((w[k][t] > 0).mean()) for k in MK}

# ---------------- 2. stats recompute vs results/df7_trend_stats.json
J = json.load(open('/mnt/project-files/research/df1/results/df7_trend_stats.json'))
def st(x, f=252):
    return dict(mean_ann=float(x.mean() * f), vol_ann=float(x.std() * np.sqrt(f)), sharpe=float(x.mean() / x.std() * np.sqrt(f)),
                cagr_ex=float(np.prod(1 + x) ** (f / len(x)) - 1))
T = tr[tr.index >= '1986-01-01']
mine = {'1986_2014': st(T), '1986_1999': st(T[T.index < '2000-01-01']), '2000_2014': st(T[T.index >= '2000-01-01'])}
ndx = S['NDX'].reindex(T.index); spx = S['SPX'].reindex(T.index)
mine['corr_ndx'] = float(np.corrcoef(T, ndx.fillna(0))[0, 1]); mine['corr_spx'] = float(np.corrcoef(T, spx.fillna(0))[0, 1])
mine['ndx_nan_1986_2014'] = int(ndx.isna().sum())
mine['gross_lev_mean'] = float(w.abs().sum(axis=1)[T.index].mean())
yr = (1 + T).groupby(T.index.year).prod() - 1
mine['years_maxdiff'] = float(max(abs(yr[y] - J['years'][str(y)]) for y in yr.index))
diffs = {}
for p in ('1986_2014', '1986_1999', '2000_2014'):
    for k in J[p]: diffs[p + '.' + k] = abs(mine[p][k] - J[p][k])
for k in ('corr_ndx', 'corr_spx', 'gross_lev_mean'): diffs[k] = abs(mine[k] - J[k])
mine['max_diff_vs_json'] = float(max(diffs.values()))
# monthly-frequency corr with NDX / SPX
Tm = (1 + T).groupby(T.index.to_period('M')).prod() - 1
nm = (1 + ndx.fillna(0)).groupby(T.index.to_period('M')).prod() - 1
sm = (1 + spx).groupby(T.index.to_period('M')).prod() - 1
mine['corr_ndx_monthly'] = float(np.corrcoef(Tm, nm)[0, 1]); mine['corr_spx_monthly'] = float(np.corrcoef(Tm, sm)[0, 1])
# conditional: NDX worst months
q = nm <= nm.quantile(0.1)
mine['trend_mean_in_ndx_worst10pct_months'] = float(Tm[q].mean()); mine['ndx_mean_in_those'] = float(nm[q].mean())
mine['trend_mean_other_months'] = float(Tm[~q].mean())
# turnover (sum |dw| per year) and cost sensitivity
dw = w.diff().abs().sum(axis=1)[T.index]
mine['turnover_ann'] = float(dw.sum() / (len(T) / 252))
mine['cost_drag_ann'] = {'%dbp' % c: float(dw.sum() / (len(T) / 252) * c / 1e4) for c in (2, 5, 10)}
R['stats'] = mine; R['stats_json'] = {p: J[p] for p in ('1986_2014', '1986_1999', '2000_2014')}

# ---------------- 3. decomposition by market and sub-period
C = (w * ex.fillna(0.0))
per = {'1986_2014': ('1986-01-01', '2014-12-31'), '1986_1999': ('1986-01-01', '1999-12-31'), '2000_2014': ('2000-01-01', '2014-12-31'),
       '2009_2014': ('2009-01-01', '2014-12-31')}
dec = {}
for p, (a, b) in per.items():
    m = (C.index >= a) & (C.index <= b); c = C[m]; ww = w[m]; ee = ex[m].fillna(0.0)
    tot = float(c.sum(axis=1).mean() * 252)
    row = {'total_mean_ann': tot}
    for k in MK:
        mk = float(c[k].mean() * 252)
        # drift (static) vs timing: mean(w*e) = mean(w)*mean(e) + cov(w,e)
        drift = float(ww[k].mean() * ee[k].mean() * 252); timing = mk - drift
        row[k] = dict(contrib_ann=mk, share=mk / tot, mean_w=float(ww[k].mean()), mean_abs_w=float(ww[k].abs().mean()),
                      mkt_ex_ann=float(ee[k].mean() * 252), drift_part=drift, timing_part=timing,
                      long_pnl_ann=float((c[k].where(ww[k] > 0, 0.0)).mean() * 252), short_pnl_ann=float((c[k].where(ww[k] < 0, 0.0)).mean() * 252),
                      vol_contrib_ann=float(c[k].std() * np.sqrt(252)))
    row['drift_total'] = sum(row[k]['drift_part'] for k in MK); row['timing_total'] = tot - row['drift_total']
    dec[p] = row
R['decomp'] = dec
y30 = src['y30']; R['y30'] = {d_: float(y30[y30.index <= d_].iloc[-1]) for d_ in ('1985-12-31', '1999-12-31', '2014-12-31')}

# ---------------- 3b. counterfactual: markets with zero drift (demeaned excess, signals recomputed). Calibration device, not a rule.
cf = {}
def demean(ex, ks, a='1984-01-01'):
    e = ex.copy()
    for k in ks:
        m = e.index >= a; e.loc[m, k] = e.loc[m, k] - e.loc[m, k].mean()
    return e
for nm_, ks in (('LTT0', ['LTT']), ('LTT0_GOLD0', ['LTT', 'GOLD']), ('ALL0', MK), ('LTT0_GOLD0_USD0', ['LTT', 'GOLD', 'USD'])):
    e2 = demean(ex, ks); w2, t2 = trend(e2); t2 = t2[t2.index >= '1986-01-01']
    cf[nm_] = {p: st(t2[(t2.index >= a) & (t2.index <= b)]) for p, (a, b) in per.items()}
    cf[nm_]['ratio_mean_vs_proxy_1986_2014'] = cf[nm_]['1986_2014']['mean_ann'] / mine['1986_2014']['mean_ann']
R['counterfactual_zero_drift'] = cf
# leave-one-market-out (weights unchanged, contribution removed) is just total - contrib; also proxy without LTT market (N=4 re-scaled)
for drop in ('LTT', 'SPX'):
    e3 = ex.drop(columns=[drop]); w3, t3 = trend(e3); t3 = t3[t3.index >= '1986-01-01']
    R['without_' + drop] = {p: st(t3[(t3.index >= a) & (t3.index <= b)]) for p, (a, b) in per.items()}

# ---------------- 4. AQR TSMOM (gross hypothetical), monthly
A = pd.read_csv('/mnt/project-files/research/data/trend_aqr/tsmom_monthly_le2014.csv', parse_dates=['date']).set_index('date')
A = A[A.index <= END]; assert A.index.max() <= END
A.index = A.index.to_period('M')
rfm = (1 + rf).groupby(idx.to_period('M')).prod() - 1
Pm = (1 + tr).groupby(idx.to_period('M')).prod() - 1
mm = pd.period_range('1986-01', '2014-12', freq='M')
a_ = A['TSMOM'].reindex(mm); p_ = Pm.reindex(mm); r_ = rfm.reindex(mm)
assert a_.notna().all() and p_.notna().all()
aq = {}
pm = {'1986_2014': ('1986-01', '2014-12'), '1986_1999': ('1986-01', '1999-12'), '2000_2014': ('2000-01', '2014-12'), '2009_2014': ('2009-01', '2014-12'),
      '1986_1992': ('1986-01', '1992-12'), '1993_1999': ('1993-01', '1999-12'), '2000_2007': ('2000-01', '2007-12'), '2008_2014': ('2008-01', '2014-12')}
for p, (a, b) in pm.items():
    sl = slice(pd.Period(a, 'M'), pd.Period(b, 'M'))
    aq[p] = dict(aqr=st(a_[sl], 12), proxy=st(p_[sl], 12), corr=float(np.corrcoef(a_[sl], p_[sl])[0, 1]),
                 aqr_sub={k: st(A[k].reindex(mm)[sl], 12)['sharpe'] for k in ('CM', 'EQ', 'FI', 'FX')})
R['aqr_vs_proxy'] = aq
R['aqr_year'] = {str(y): float(np.prod(1 + a_[a_.index.year == y]) - 1) for y in range(2008, 2015)}
R['proxy_year_m'] = {str(y): float(np.prod(1 + p_[p_.index.year == y]) - 1) for y in range(2008, 2015)}
# AQR sector P&L shares (equal-weight of 4 sectors? check TSMOM ~ mean of sectors)
R['aqr_tsmom_vs_mean_sectors_corr'] = float(np.corrcoef(a_, A[['CM', 'EQ', 'FI', 'FX']].reindex(mm).mean(axis=1))[0, 1])
R['aqr_FI_share_hint'] = {k: float(A[k].reindex(mm).mean() * 12) for k in ('CM', 'EQ', 'FI', 'FX', 'TSMOM')}

# ---------------- 4b. fee model (estimate): scale gross excess to target vol, add T-bill, charge 2% mgmt + 20% perf with monthly HWM
def fees(gx, rfm, mg=0.02, pf=0.20, hurdle=True, tc=0.0):
    """gx: monthly gross excess return (already vol-scaled); returns monthly net excess return. tc = annual trading-cost drag."""
    nav = 1.0; hwm = 1.0; bench = 1.0; out = []
    for g, r in zip(gx.values, rfm.values):
        gross = nav * (1 + r + g - tc / 12)
        after_mg = gross - nav * mg / 12
        bench *= (1 + r)
        if hurdle:   # perf fee on NAV above HWM grown at T-bill
            base = hwm * (1 + r); hwm_r = base
        else:
            base = hwm; hwm_r = hwm
        perf = pf * max(after_mg - base, 0.0)
        new = after_mg - perf
        hwm = max(hwm_r, new) if hurdle else max(hwm, new)
        out.append(new / nav - 1 - r); nav = new
    return pd.Series(out, index=gx.index)
fe = {}
for nm_, ser in (('AQR', a_), ('PROXY', p_)):
    for tv in (0.10, 0.13):
        sc = tv / (ser.std() * np.sqrt(12)); g = ser * sc
        for hd in (True, False):
            for tc in (0.0, 0.01):
                n = fees(g, r_, hurdle=hd, tc=tc)
                key = '%s_vol%d_%s_tc%d' % (nm_, int(tv * 100), 'hurdleTbill' if hd else 'noHurdle', int(tc * 100))
                fe[key] = {p: dict(gross_mean=float(g[slice(pd.Period(a, 'M'), pd.Period(b, 'M'))].mean() * 12),
                                   net_mean=float(n[slice(pd.Period(a, 'M'), pd.Period(b, 'M'))].mean() * 12),
                                   net_sharpe=st(n[slice(pd.Period(a, 'M'), pd.Period(b, 'M'))], 12)['sharpe'])
                           for p, (a, b) in pm.items() if p in ('1986_2014', '1986_1999', '2000_2014', '2009_2014')}
                fe[key]['kept_frac_1986_2014'] = fe[key]['1986_2014']['net_mean'] / fe[key]['1986_2014']['gross_mean']
R['fees'] = fe
# DF7 convention at proxy vol: 50% of proxy mean, minus 0.85%
pmean = mine['1986_2014']['mean_ann']; pvol = mine['1986_2014']['vol_ann']
R['convention'] = dict(prim_ex=0.5 * pmean, prim_ex_after_dbmf_fee=0.5 * pmean - 0.0085, prim_sharpe_after_fee=(0.5 * pmean - 0.0085) / pvol,
                       q_ex_after_fee=0.25 * pmean - 0.0085, q_sharpe_after_fee=(0.25 * pmean - 0.0085) / pvol,
                       aqr_sharpe_at_proxy_vol_mean=aq['1986_2014']['aqr']['sharpe'] * pvol, rf_ann_1986_2014=float(r_.mean() * 12))
json.dump(R, open(OUT, 'w'), indent=1, default=str)
print(json.dumps(R, indent=1, default=str)[:20000])
