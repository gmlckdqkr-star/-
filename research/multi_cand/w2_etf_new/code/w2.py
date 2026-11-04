"""MC1 W2: non-NDX return streams gated by lagged CPI information, combined with s0.85 (MS1 std contexts, <=2014).
See ../PRECOMMIT_W2.md. Output ../results/w2_main.json (+ printed lines)."""
import sys, os, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import jp, ov
OUT = '/mnt/project-files/research/multi_cand/w2_etf_new/results/'
WARM = ov.WARM; YD = 252; SEAL = pd.Timestamp('2014-12-31')
CPI_F = '/mnt/project-files/research/clean_regime/data/SHILLER_ie_data_IA_20141222172333_le2014.csv'
GOLD_F = '/mnt/project-files/research/data/gold/xauusd_twelvedata_1day_raw.csv'
ER3 = (0.0095 + 0.015) / 252; COST = 0.003; TAX = 0.22

# ---------------- CPI (point-in-time: month m usable from first trading day of month m+2)
def cpi_daily(idx):
    c = pd.read_csv(CPI_F); c['m'] = pd.to_datetime(c['Month'] + '-01'); c = c.set_index('m')['Consumer Price Index CPI'].astype(float)
    c = c[c.index <= SEAL]
    yoy = c / c.shift(12) - 1
    tr6 = yoy - yoy.shift(6)                       # >0 = inflation rising
    s = pd.DataFrame({'yoy': yoy, 'tr6': tr6}); s.index = s.index + pd.offsets.MonthBegin(2)
    return s.reindex(idx, method='ffill')          # NaN before first usable month

def gold_ret(idx):
    g = pd.read_csv(GOLD_F, sep=';', parse_dates=['datetime']).set_index('datetime')['close'].sort_index()
    g = g[g.index <= SEAL]; lv = g.reindex(idx, method='ffill'); r = lv.pct_change()
    r[lv.isna() | lv.shift(1).isna()] = np.nan
    return r

# ---------------- source frame on a context calendar
CAL = {'dev250_path': ('1986-01-02', '2014-12-31'), 'real_ndx_86_14': ('1984-01-03', '2014-12-31'),
       'real_spx_70_85': ('1928-01-03', '1985-12-31')}
def source(bn):
    a, b = CAL[bn]; R, M = jp.calendar(a, b); idx = R.index; assert idx[-1] <= SEAL
    rf = M['rf'].fillna(0).values
    S = pd.DataFrame(index=idx)
    S['rf'] = rf; S['cash'] = np.maximum(rf - 0.02 / 252, 0) * (1 - 0.154)
    b10 = R['B10'].fillna(0).values; b30 = R['B30'].values; b30 = np.where(np.isnan(b30), b10, b30)
    S['B3'] = 3 * b10 - 2 * rf - ER3; S['B1'] = b10 - 0.002 / 252; S['L3'] = 3 * b30 - 2 * rf - ER3
    S['EN'] = R['ENER'].fillna(0).values - 0.002 / 252
    g = gold_ret(idx); S['GD'] = (g - 0.004 / 252).values; S['gold_ok'] = g.notna().values
    S['GD'] = S['GD'].fillna(0)
    C = cpi_daily(idx); S['yoy'] = C['yoy'].values; S['tr6'] = C['tr6'].values
    S['y10'] = M['y10'].values / 100; S['rfa'] = rf * 252
    stream = 'SPX' if bn.startswith('real_spx') else 'NDX'
    S['eq'] = R[stream].fillna(0).values
    lr_e = np.log1p(S['eq']); lr_b = np.log1p(R['B10'].fillna(0))
    S['corr126'] = lr_e.rolling(126).corr(lr_b).values
    return S

# ---------------- hypotheses: target weights {asset: w(t)} decided at close t (NaN signal -> off)
def tgt(S, hid, shift=0):
    y = S['yoy'].values; tr = S['tr6'].values; ok = ~np.isnan(y)
    def g(cond): return np.where(ok & np.nan_to_num(cond, nan=0).astype(bool), 1.0, 0.0)
    if hid == 'H1':    w = {'B3': g(y < 0.03)}
    elif hid == 'H1b': w = {'B1': g(y < 0.03)}
    elif hid == 'H1s25': w = {'B3': g(y < 0.025)}
    elif hid == 'H1s35': w = {'B3': g(y < 0.035)}
    elif hid == 'H1L': w = {'L3': g(y < 0.03)}
    elif hid == 'H2':  w = {'B3': g((S['y10'].values - y) > 0.02)}
    elif hid == 'H3':  w = {'B3': g(np.where(np.isnan(tr), False, tr <= 0))}
    elif hid == 'H4':  w = {'GD': g((S['rfa'].values - y) < 0.01) * S['gold_ok'].values}
    elif hid == 'H5':  lo = g(y < 0.03); w = {'B3': lo, 'EN': ok * (1 - lo)}
    elif hid == 'H6':  w = {'EN': g((y > 0.03) & np.where(np.isnan(tr), False, tr > 0))}
    elif hid == 'H7':  c = S['corr126'].values; w = {'B3': np.where(np.isnan(c), 0.0, (c < 0).astype(float))}
    elif hid == 'A_B3': w = {'B3': np.ones(len(S))}
    elif hid == 'A_B1': w = {'B1': np.ones(len(S))}
    elif hid == 'A_EN': w = {'EN': np.ones(len(S))}
    elif hid == 'A_GD': w = {'GD': S['gold_ok'].values.astype(float)}
    elif hid.startswith('X_'):      # exposure-matched constant: X_<asset>_<w>
        _, a, v = hid.split('_'); w = {a: np.full(len(S), float(v))}
    else: raise KeyError(hid)
    if shift:   # null: circular time shift of the gate (only over rows where the signal exists)
        for a in w:
            x = w[a].copy(); m = ok if not hid == 'H7' else ~np.isnan(S['corr126'].values)
            j = np.where(m)[0]; x[j] = np.roll(x[j], shift); w[a] = x
    return w

def eff(w):   # decision at close t, trade at close t+2 -> earns from return t+3
    return {a: np.r_[np.zeros(3), v[:-3]] for a, v in w.items()}

def stream_on(S, w, ii):
    """per-path daily net (after cost, before tax) sleeve return, shape (P, T-WARM)"""
    we = eff(w); P = ii.shape[0]
    tot = np.zeros(ii.shape); x = np.zeros(ii.shape); cost = np.zeros(ii.shape)
    for a, v in we.items():
        wp = v[ii]; x += wp * S[a].values[ii]; tot += wp
        cost[:, 1:] += COST * np.abs(np.diff(wp, axis=1))
    x += (1 - tot) * S['cash'].values[ii]
    x = x - cost
    return x[:, WARM:], tot[:, WARM:]

# ---------------- standalone stats
def standalone(x, rfp):
    P, T = x.shape; yrs = T / YD
    V = np.ones(P); E = np.empty((P, T)); D = 0.25
    for y in range(int(np.ceil(T / YD))):
        a, b = y * YD, min((y + 1) * YD, T); V0 = V.copy()
        E[:, a:b] = V0[:, None] * np.cumprod(1 + x[:, a:b], axis=1); V = E[:, b - 1].copy()
        V = V - TAX * np.maximum(V - V0 - D, 0); E[:, b - 1] = V
    cagr = np.maximum(V, 1e-9) ** (1 / yrs) - 1
    ex = x - rfp; sh = ex.mean(1) / ex.std(1) * np.sqrt(YD)
    lv = np.cumprod(1 + x, axis=1); mdd = (lv / np.maximum.accumulate(lv, axis=1) - 1).min(1)
    exat = np.diff(np.log(np.c_[np.ones(P), E]), axis=1) - np.log1p(rfp); sh_at = exat.mean(1) / exat.std(1) * np.sqrt(YD)
    return dict(cagr_at=float(np.median(cagr)), sharpe=float(np.median(sh)), sharpe_at=float(np.median(sh_at)),
                mdd=float(np.median(mdd)), cagr_p10=float(np.percentile(cagr, 10)))

# ---------------- combo with s0.85
def combo(EE, L, x, w1, mcost=COST, start=0):
    """EE: s0.85 after-tax curve (P,T); L: liquidation factor fin/EE_end; x: sleeve net returns (P,T); w1: s0.85 weight.
    Yearly (252 path days) rebalance from column `start`; sleeve gain taxed 22% each year (no deduction); s0.85 leg liquidation via L."""
    P = EE.shape[0]; b0 = np.ones(P) if start == 0 else EE[:, start - 1]
    E = np.c_[b0, EE[:, start:]]; x = x[:, start:]; T = x.shape[1]; yrs = T / YD
    V1 = np.full(P, w1); V2 = np.full(P, 1 - w1); W = np.empty((P, T))
    for y in range(int(np.ceil(T / YD))):
        a, b = y * YD, min((y + 1) * YD, T)
        c1 = E[:, a + 1:b + 1] / E[:, a][:, None]; c2 = np.cumprod(1 + x[:, a:b], axis=1)
        W[:, a:b] = V1[:, None] * c1 + V2[:, None] * c2
        V1n = V1 * c1[:, -1]; V2n = V2 * c2[:, -1]
        V2n = V2n - TAX * np.maximum(V2n - V2, 0)
        if b < T:
            tot = V1n + V2n; tr = np.abs(w1 * tot - V1n); tot = tot - mcost * tr
            V1, V2 = w1 * tot, (1 - w1) * tot
        else: V1, V2 = V1n, V2n
    fin = V1 * L + V2
    cagr = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
    mdd = (W / np.maximum.accumulate(W, axis=1) - 1).min(1)
    return cagr, mdd

HYP = ['H1', 'H1b', 'H1s25', 'H1s35', 'H1L', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7']
BASE = ['A_B3', 'A_B1', 'A_EN', 'A_GD']
NULLS = (1800, 2700, 3600)

def main():
    t0 = time.time(); C = std.contexts(); res = {'meta': dict(precommit_sha='3245a60f4748', ms1_std='ee4de887037c')}
    for bn in ('real_ndx_86_14', 'dev250_path', 'real_spx_70_85'):
        c = C[bn]; S = source(bn); ii = c.ii
        # calendar check: std's r == our calendar's r on the same ii
        chk = np.nanmax(np.abs(c.r[:, 1:] - S['eq'].values[ii][:, 1:]))
        cg, EE = std.engine(c, *std.s085(c)); yrs = EE.shape[1] / YD
        fin = (1 + cg) ** yrs; L = fin / EE[:, -1]
        rfp = S['rf'].values[ii][:, WARM:]
        print(bn, 'calendar max|dr| %.2e' % chk, 's085 med %.4f' % np.median(cg), 'L med %.3f' % np.median(L), flush=True)
        base_c, base_m = combo(EE, L, np.zeros_like(EE), 1.0)
        R = {'calendar_check': float(chk), 's085': float(np.median(cg)), 's085_combo_machine': float(np.median(base_c)),
             's085_mdd': float(np.median(base_m))}
        if bn == 'real_ndx_86_14':
            r85 = EE[0, 1:] / EE[0, :-1] - 1; req = c.r[0, WARM + 1:]
        for hid in HYP + BASE:
            w = tgt(S, hid)
            if hid in ('H4', 'A_GD'):      # gold: real 1999-2014 only
                if bn != 'real_ndx_86_14': continue
            x, tot = stream_on(S, w, ii)
            row = dict(expo=float(tot.mean()))
            st = 0
            if hid in ('H4', 'A_GD'):
                d0 = S.index[ii[0, WARM:]]; st = int(np.searchsorted(d0, pd.Timestamp('1999-01-04')))
                row['window'] = '1999-01-04..2014-12-31'
                row.update(standalone(x[:, st:], rfp[:, st:]))
            else:
                row.update(standalone(x, rfp))
            if bn == 'real_ndx_86_14':
                xs = x[0, 1 + st:]; a = r85[st:]
                row['corr_s085'] = float(np.corrcoef(xs, a)[0, 1])
                row['spearman_s085'] = float(pd.Series(xs).corr(pd.Series(a), method='spearman'))
                row['corr_ndx'] = float(np.corrcoef(xs, req[st:])[0, 1])
            for w1 in (0.8, 0.7):
                if st:
                    b0, _ = combo(EE, L, np.zeros_like(EE), 1.0, start=st)
                    cc, mm = combo(EE, L, x, w1, start=st); d = cc - b0
                else:
                    cc, mm = combo(EE, L, x, w1); d = cc - base_c
                k = 'm%d' % round(w1 * 100)
                row[k] = dict(cagr=float(np.median(cc)), d=float(np.median(d)), pwin=float(np.mean(d > 1e-6)),
                              mdd=float(np.median(mm)), dd80=float(np.mean(mm <= -0.8)))
                if st: row[k]['base_window'] = float(np.median(b0))
                cc6, _ = combo(EE, L, x, w1, mcost=2 * COST, start=st) if st else combo(EE, L, x, w1, mcost=2 * COST)
                row[k]['d_cost06'] = float(np.median(cc6 - (b0 if st else base_c)))
            # information value checks for gated streams
            if hid in HYP:
                a = list(w.keys())
                if len(a) == 1 and hid not in ('H4',):
                    em = 'X_%s_%.3f' % (a[0], float(np.mean(w[a[0]][~np.isnan(S['yoy'].values)])) if hid != 'H7' else float(np.mean(w[a[0]])))
                    xm, _ = stream_on(S, tgt(S, em), ii)
                    cm, _ = combo(EE, L, xm, 0.8); row['expo_matched_m80_d'] = float(np.median(cm - base_c)); row['expo_matched_id'] = em
                    row['gate_minus_matched_m80'] = float(np.median(combo(EE, L, x, 0.8)[0] - cm))
                if hid not in ('H4',):
                    nd = []
                    for k in NULLS:
                        xn, _ = stream_on(S, tgt(S, hid, shift=k), ii); cn, _ = combo(EE, L, xn, 0.8); nd.append(float(np.median(cn - base_c)))
                    row['null_shift_m80_d'] = nd
            R[hid] = row
            print('%-15s %-6s expo %.2f | alone AT %.3f SR %.2f mdd %.2f | corr %s | m80 d %+.4f pw %.2f | m70 d %+.4f | %s' % (
                bn, hid, row['expo'], row['cagr_at'], row['sharpe'], row['mdd'], ('%.2f' % row['corr_s085']) if 'corr_s085' in row else '-',
                row['m80']['d'], row['m80']['pwin'], row['m70']['d'],
                ('null %s matched %+.4f' % (['%+.4f' % v for v in row.get('null_shift_m80_d', [])], row.get('expo_matched_m80_d', np.nan)))), flush=True)
        res[bn] = R
        json.dump(res, open(OUT + 'w2_main.json', 'w'), indent=1)
    print('done %.0fs' % (time.time() - t0))

if __name__ == '__main__':
    main()
