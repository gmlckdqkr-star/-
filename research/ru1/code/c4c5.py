"""C4 KRW tax / KRW wealth with real USD/KRW (FRED DEXKOUS, NY noon, <=2014; co-sampled with the dev250 date blocks).
C5 monthly deposits (1% of the start amount, every 21 trading days) with the contract's 4-business-day wait rule vs buy at once.
C6 drawdown experience (app account, USD and KRW)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru, std
from std import jp, ov, iv
W = ru.WARM; B = ac3.prep()
fx = pd.read_csv('/mnt/project-files/research/data/fx_dexkous/raw/DEXKOUS_raw.csv', na_values='.', parse_dates=['observation_date']).set_index('observation_date')['DEXKOUS']
fx = fx[fx.index <= pd.Timestamp('2014-12-31')].dropna()
def fx_index(cal_idx, ii):
    """cal_idx: calendar DatetimeIndex of the basis; ii: (P, T) rows -> X (P, T) with X[:, W] == 1"""
    f = fx.reindex(cal_idx).ffill().bfill().values; lr = np.r_[0.0, np.diff(np.log(f))]
    X = np.exp(np.cumsum(lr[ii], axis=1)); return X / X[:, W:W + 1]
R, M = jp.calendar('1984-01-03', '2014-12-31'); cal_real = R.index
a, b, P, blk, seed = iv.POOLS['dev250']; Rd, Md = jp.calendar(a, b); cal_dev = Rd.index
C = std.contexts()
XX = {'real_ndx_86_14': fx_index(cal_real, C['real_ndx_86_14'].ii), 'dev250_path': fx_index(cal_dev, C['dev250_path'].ii)}
out = {'fx_note': 'DEXKOUS failed the A10-1 gate for SIGNAL use (2008 noise, fixing time); used here only to translate values and tax at trade dates.'}
for bn in ('real_ndx_86_14', 'dev250_path'):
    b0 = B[bn]; Pn, T = b0['R'].shape; n = T - W; y = n / 252; X = XX[bn]; Z = np.zeros((Pn, n)); one = np.ones((Pn, T))
    def go(Xa, krw, fxc, dep=Z, wait=0):
        return ru.acctP(b0['R'], b0['RF'], b0['L'], np.ascontiguousarray(Xa), np.ascontiguousarray(dep), krw, wait, fxc, .003, .22, .25, .0245, 1.0)
    o0, E0, _ = go(one, 0, 0.0)                      # B0: USD, MS1 tax
    o1, E1, K1 = go(X, 0, 0.0)                       # USD-basis tax, values translated to KRW
    o2, E2, K2 = go(X, 1, 0.0)                       # Korean rule: KRW basis at trade-date FX
    o3, E3, K3 = go(X, 1, 0.0025)                    # + 0.25% conversion at start and end
    g0 = ru.cagr(o0[:, 0], y); gu2 = ru.cagr(o2[:, 0], y); gk1 = ru.cagr(o1[:, 1], y); gk2 = ru.cagr(o2[:, 1], y); gk3 = ru.cagr(o3[:, 1], y)
    fxcagr = X[:, -1] ** (1 / y) - 1
    mk = (K3 / np.maximum.accumulate(K3, 1) - 1).min(1); mu = (E0 / np.maximum.accumulate(E0, 1) - 1).min(1)
    r = dict(B0_usd=dict(p50=float(np.median(g0)), p10=float(np.percentile(g0, 10)) if Pn > 1 else None, mdd_med=float(np.median(mu)), dd80=float(np.mean(mu <= -.8))),
             krwtax_in_usd=dict(p50=float(np.median(gu2)), d_med_vs_B0=float(np.median(gu2 - g0)), p_worse=float(np.mean(gu2 < g0 - 1e-6))),
             krw_wealth_usdtax=dict(p50=float(np.median(gk1))),
             krw_wealth_krwtax=dict(p50=float(np.median(gk2)), d_med_vs_usdtax=float(np.median(gk2 - gk1))),
             krw_wealth_krwtax_fx025=dict(p50=float(np.median(gk3)), p10=float(np.percentile(gk3, 10)) if Pn > 1 else None, mdd_krw_med=float(np.median(mk)), dd80_krw=float(np.mean(mk <= -.8))),
             fx_cagr_med=float(np.median(fxcagr)), tax_paid_krw_med_usdbasis=float(np.median(o1[:, 5])), tax_paid_krw_med_krwbasis=float(np.median(o2[:, 5])),
             final_wealth_krw_med_krwtax=float(np.median(o3[:, 1])))
    # C5 deposits: 1% of start every 21 trading days from day 21 (KRW units), MS1 USD mode to isolate the rule
    dep = np.zeros((Pn, n)); dep[:, 21::21] = 0.01
    oa, Ea, _ = go(one, 0, 0.0, dep, 1); ob, Eb, _ = go(one, 0, 0.0, dep, 0)
    ratio = oa[:, 0] / ob[:, 0] - 1
    r['C5_deposits'] = dict(deposits_total=float(dep[0].sum()), wait_share_med=float(np.median(oa[:, 7] / max(dep[0].astype(bool).sum(), 1))),
                            waited_cash_days_med=float(np.median(oa[:, 8])), final_ratio_wait_vs_now_med=float(np.median(ratio)),
                            final_ratio_p10=float(np.percentile(ratio, 10)) if Pn > 1 else float(ratio[0]), p_wait_worse=float(np.mean(ratio < -1e-9)))
    # C6 drawdown experience on the app account (USD) and KRW (with KRW tax)
    lo_u, b50_u = ru.underwater(E0); lo_k, b50_k = ru.underwater(K3)
    r['C6_experience'] = dict(longest_underwater_years_med=float(np.median(lo_u)), longest_underwater_years_p90=float(np.percentile(lo_u, 90)),
                              share_days_below_half_med=float(np.median(b50_u)), krw_longest_underwater_years_med=float(np.median(lo_k)),
                              krw_share_days_below_half_med=float(np.median(b50_k)), trades_per_year_med=float(np.median(o0[:, 4]) / y))
    out[bn] = r; print(bn, json.dumps(r, indent=None)[:1500], flush=True)
json.dump(out, open('/mnt/project-files/research/ru1/results/c4c5c6.json', 'w'), indent=1)
