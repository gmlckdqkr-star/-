"""M3 (b) KRW-basis currency structures (PRECOMMIT_M3 sec 5, report only; MS1 USD headline unchanged).
s0.85 in-force levels on real_ndx_86_14 (state carried from 1986), new KRW 10M account at each window start, upeng.run_port with:
  22 % yearly on realized net gains of TQQQ measured in KRW (FX gains included), D = 2.5M KRW, final liquidation tax;
  USD deposit: interest 15.4 % (already in the return), FX gain tax-free (notax); KRW deposit: max(i_KR - 2 %p, 0) x (1 - 15.4 %).
Structures: B0 TQQQ unhedged + USD cash, B1 TQQQ unhedged + KRW cash, B2 TQQQ hedged + USD cash, B3 TQQQ hedged + KRW cash.
Hedged TQQQ (KRW) = (1 + r3)(1 + (i_KR - i_US - hc)/252) - 1, taxable as one product. FX conversion adds fxc per side on B1/B3 trades."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env
G = m3env.G; E = G.E; WARM = G.WARM; SCR = m3env.SCR
WIN = {'1991_2014': ('1991-01-02', '2014-12-31'), '1991_1996': ('1991-01-02', '1996-12-31'),
       '1997_1998': ('1997-01-02', '1998-12-31'), '1999_2014': ('1999-01-04', '2014-12-31')}


def inputs():
    b = G.Basis('real_ndx_86_14'); L = G.s085_levels('real_ndx_86_14')[0]
    dates = b.D.index[b.c.ii[0]]                                      # row dates (T,)
    fx = pd.read_csv(SCR + 'data/dexkous_le2014.csv', parse_dates=['date']).set_index('date')['krw']
    fx = fx[fx.index <= '2014-12-31']
    fxd = fx.reindex(fx.index.union(dates)).ffill().reindex(dates)
    fxr = fxd.pct_change().fillna(0.0).values
    o = pd.read_csv(SCR + 'data/oecd_kei_kor_usa_le2014.csv')
    kr = o[(o.REF_AREA == 'KOR') & (o.MEASURE == 'IR3TIB')].set_index('TIME_PERIOD')['OBS_VALUE'] / 100.0
    us3 = o[(o.REF_AREA == 'USA') & (o.MEASURE == 'IR3TIB')].set_index('TIME_PERIOD')['OBS_VALUE'] / 100.0
    ym = pd.Index(dates.strftime('%Y-%m'))
    ikr = kr.reindex(ym).values; ius_oecd = us3.reindex(ym).values
    rf = np.asarray(b.c.rf, float)[0]; r = np.asarray(b.c.r, float)[0]
    return dict(dates=dates, L=L, fxr=fxr, fxlvl=fxd.values, ikr=ikr, ius_oecd=ius_oecd, rf=rf, r=r)


def products(I, hc=0.003):
    rf, r, fxr, ikr = I['rf'], I['r'], I['fxr'], I['ikr']
    r3 = 3 * r - 2 * rf - 0.0245 / 252
    cu = np.maximum(rf - 0.02 / 252, 0.0) * (1 - 0.154)
    iusa = rf * 252                                                    # MS1 US short rate (annualized) for the carry
    carry = (ikr - iusa - hc) / 252
    ck = np.maximum((ikr - 0.02) / 252, 0.0) * (1 - 0.154)
    return {'TQQQ_U': (1 + r3) * (1 + fxr) - 1, 'TQQQ_H': (1 + r3) * (1 + carry) - 1, 'TQQQ_USD': r3,
            'CASH_USD_K': (1 + cu) * (1 + fxr) - 1, 'CASH_KRW': ck, 'CASH_USD': cu}


STRUCT = {'B0': ('TQQQ_U', 'CASH_USD_K', False), 'B1': ('TQQQ_U', 'CASH_KRW', True), 'B2': ('TQQQ_H', 'CASH_USD_K', False),
          'B3': ('TQQQ_H', 'CASH_KRW', True), 'USD': ('TQQQ_USD', 'CASH_USD', False),
          # decomposition only (not a structure choice): hedge with zero carry (FX removed, no rate differential)
          'B2c0': ('TQQQ_USD', 'CASH_USD_K', False), 'B3c0': ('TQQQ_USD', 'CASH_KRW', True)}


def run_struct(I, P, name, win, fxc=0.001, cost=0.003):
    on, cash, conv = STRUCT[name]
    a, e = WIN[win]; d = I['dates'][WARM:]
    k0 = int(np.searchsorted(d, pd.Timestamp(a))); k1 = int(np.searchsorted(d, pd.Timestamp(e), side='right'))
    rr = np.stack([P[on][WARM + k0:WARM + k1], P[cash][WARM + k0:WARM + k1]], axis=1).copy(); rr[0] = 0.0
    assert np.all(np.isfinite(rr)), (name, win)
    lv = I['L'][k0:k1]; K = len(lv)
    W = np.zeros((1, K, 2)); W[0, :, 0] = lv / 3; W[0, :, 1] = 1 - lv / 3
    fl = np.r_[True, np.diff(lv) != 0][None, :]
    out = np.zeros(7); cur = np.zeros(K)
    E.run_port(np.ascontiguousarray(rr), np.zeros_like(rr), np.zeros_like(rr), W, fl, np.array([1.0]), np.zeros(K, bool), 0.0,
               np.array([False, True]), cost + (fxc if conv else 0.0), 0.22, 0.25, 0.154, out, cur)
    yrs = K / 252; cg = max(out[0], 1e-9) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(cur); mdd = float(np.min(cur / pk - 1))
    return dict(cagr=float(cg), final=float(out[0]), mdd=mdd, years=yrs, tax_paid=float(out[6]), trades_pa=float(out[4] / yrs))


if __name__ == '__main__':
    I = inputs(); res = {}
    d = I['dates'][WARM:]
    for win, (a, e) in WIN.items():
        m = (d >= pd.Timestamp(a)) & (d <= pd.Timestamp(e)); lv = I['L'][m]
        k0 = np.searchsorted(I['dates'], d[m][0]); k1 = np.searchsorted(I['dates'], d[m][-1])
        res[win] = {'_info': dict(idle_share=float(np.mean(1 - lv / 3)), krw_start=float(I['fxlvl'][k0]), krw_end=float(I['fxlvl'][k1]),
                                  ikr_mean=float(np.nanmean(I['ikr'][WARM:][m])), ius_mean=float(np.mean(I['rf'][WARM:][m]) * 252))}
    for tag, kw, hc in (('base', {}, 0.003), ('fxc05', {'fxc': 0.005}, 0.003), ('hc10', {}, 0.010)):
        P = products(I, hc=hc)
        for win in WIN:
            for s in STRUCT:
                res[win]['%s|%s' % (s, tag)] = run_struct(I, P, s, win, **kw)
    json.dump(res, open(SCR + 'results/t4_krw.json', 'w'), indent=1)
    for win in WIN:
        print('==', win, json.dumps(res[win]['_info']))
        for tag in ('base', 'fxc05', 'hc10'):
            b0 = res[win]['B0|' + tag]['cagr']
            print(tag, ' '.join('%s %.2f%% (d %+.2f, mdd %.0f%%)' % (s, 100 * res[win]['%s|%s' % (s, tag)]['cagr'],
                  100 * (res[win]['%s|%s' % (s, tag)]['cagr'] - b0), 100 * res[win]['%s|%s' % (s, tag)]['mdd']) for s in STRUCT))
