"""LH1 runs (PRECOMMIT_LH1.md sha c42c3057 + ADDENDUM_LH1_1 sha 5f03d38a): v1 unchanged on US S&P 1929-1954 with the
pre-1934 short rate filled (A: NBER m13029a via deep_history TBILL rate_known_pct; B: NBER commercial paper, FRED
M13002US35620M156NNBR). Placebo = circular flag shift 504 + 63j. Checks C1-C4. Writes results/lh1.json."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import ov, mkt, ce
DH = '/mnt/project-files/research/data/deep_history/clean/'
LD = '/mnt/project-files/research/lh1/data/'
OUT = '/mnt/project-files/research/lh1/results/lh1.json'
END = pd.Timestamp('1954-12-31')
CUT34 = pd.Timestamp('1934-02-01')
W = ov.WARM

def monthly_known(s, idx):
    s = s.copy(); s.index = s.index + pd.offsets.MonthBegin(1)
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)

def build(end, fill):
    """fill: 'A' (m13029a), 'B' (commercial paper), 'REC' (leave NaN = the recorded pipeline)."""
    a = pd.read_csv(DH + 'SPX_TR_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
    tb = pd.read_csv(DH + 'TBILL_daily_1927_2014.csv', parse_dates=['date']).set_index('date')
    r = a['tr_ret'].fillna(0.0); r = r[(r.index >= pd.Timestamp('1928-01-01')) & (r.index <= end)]
    idx = r.index; assert idx.max() <= end
    M = mkt.macro(idx)                                   # MS1 macro: y10 = ^TNX else Shiller GS10, y3m = ^IRX else TB3MS
    rf = tb['rate_known_pct'].reindex(idx).ffill()       # ADDENDUM 1: MS1 pre-1960 rf = rate_known_pct
    irx = mkt.pser('_IRX', 3).reindex(idx).ffill()
    rf = irx.where(irx.notna(), rf).fillna(0) / 100 / 252
    y3m = M['y3m'].copy(); pre = (idx < CUT34) & y3m.isna().values
    if fill == 'A': y3m[pre] = tb['rate_known_pct'].reindex(idx)[pre]
    elif fill == 'B':
        cp = pd.read_csv(LD + 'M13002US35620M156NNBR_le1954.csv', parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0]
        y3m[pre] = monthly_known(cp.astype(float), idx)[pre]
    X = pd.DataFrame({'r': r.values, 'rf': rf.values, 'y10': M['y10'].values, 'y3m': y3m.values, 'cs': M['cs'].values,
                      'vix': M['vix'].values}, index=idx)
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    return X

def acct(X, F, i0, i1=None):
    i1 = len(X) if i1 is None else i1
    c = ov.Ctx(X, F, np.arange(i0, i1)[None, :])
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    return float(cg[0]), E[0], c

def mdd(E): return float((E / np.maximum.accumulate(E) - 1).min())

def seg(E, dates, a, b):
    d = pd.DatetimeIndex(dates); j0 = d.searchsorted(pd.Timestamp(a)); j1 = d.searchsorted(pd.Timestamp(b), 'right') - 1
    yrs = (d[j1] - d[j0]).days / 365.25
    ratio = E[j1] / E[j0]
    return dict(start=str(d[j0].date()), end=str(d[j1].date()), ratio=float(ratio), cagr=float(ratio ** (1 / yrs) - 1),
                mdd=mdd(E[j0:j1 + 1]))

def run_unit(fill, placebo=True):
    X = build(END, fill); F = ov.flags_hist(X); n = len(X); i0 = 0
    dates = X.index[i0 + W:]
    a, E, c = acct(X, F, i0); assert len(E) == len(dates), (len(E), len(dates))
    out = dict(fill=fill, scored_from=str(dates[0].date()), scored_to=str(dates[-1].date()), rows=int(len(dates)),
               rows_per_cal_year=float(len(dates) / ((dates[-1] - dates[0]).days / 365.25)), A=a, A_mdd=mdd(E))
    on = (F['inv'] | F['shock6m']).iloc[i0 + W:]
    out['alarm_on_share'] = float(on.mean())
    out['alarm_on_by_year'] = {str(y): float(v) for y, v in on.groupby(on.index.year).mean().items()}
    q, Eq = std.hold(ov.Ctx(X, F, np.arange(i0, n)[None, :]), 1); out['HOLD1'] = float(q[0]); out['HOLD1_mdd'] = mdd(Eq[0])
    t, Et = std.engine(c, np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5); out['HOLD3'] = float(t[0]); out['HOLD3_mdd'] = mdd(Et[0])
    Fa = F.copy(); Fa['inv'] = True; Fn = F.copy(); Fn['inv'] = False; Fn['shock6m'] = False
    al, Ea, _ = acct(X, Fa, i0); nv, En, _ = acct(X, Fn, i0)
    out.update(ALWAYS=al, ALWAYS_mdd=mdd(Ea), NEVER=nv, NEVER_mdd=mdd(En))
    out['segments'] = {}
    for nm, (s0, s1) in {'1929-03_1932-12': ('1929-01-01', '1932-12-31'), '1933_1945': ('1933-01-01', '1945-12-31'),
                         '1946_1954': ('1946-01-01', '1954-12-31'), 'crash_1929-09-03_1932-06-01': ('1929-09-03', '1932-06-01')}.items():
        out['segments'][nm] = {k: seg(EE, dates, s0, s1) for k, EE in (('v1', E), ('hold1x', Eq[0]), ('always', Ea), ('never', En))}
    if placebo:
        rows = np.arange(i0, n); N = len(rows); pl = []; s = 504
        while s <= N - 504:
            Fs = F.copy(); Fs.iloc[rows] = F.iloc[np.roll(rows, s)].values; pl.append(acct(X, Fs, i0)[0]); s += 63
        pl = np.array(pl); S = a - float(np.median(pl)); p = (1 + int((pl >= a).sum())) / (1 + len(pl))
        verdict = 'TRANSFERS' if (S >= 0.03 and p <= 0.10) else ('DOES NOT TRANSFER' if (S <= 0 or p >= 0.5) else 'INCONCLUSIVE')
        out.update(placebo_med=float(np.median(pl)), placebo_p10=float(np.percentile(pl, 10)), placebo_p90=float(np.percentile(pl, 90)),
                   n_placebo=int(len(pl)), S=S, p=p, verdict=verdict)
    return X, F, out

def rolling(X, F):
    n = len(X); j0 = W; res = {}
    for h in (10, 20):
        L = h * 252; st = np.arange(j0, n - L + 1, 21)
        c = ov.Ctx(X, F, (st[:, None] - W) + np.arange(W + L)[None, :])
        B, bfn, bp, fs = std.s085(c); v, _ = std.engine(c, B, bfn, bp, fs, cspr=10.0); q, _ = std.hold(c, 1)
        pc = lambda z: {k: float(np.percentile(z, k)) for k in (10, 50, 90)}
        res['%dy' % h] = dict(n_windows=int(len(st)), first_start=str(X.index[st[0]].date()), last_start=str(X.index[st[-1]].date()),
                              v1=pc(v), hold1x=pc(q), share_v1_gt_1x=float(np.mean(v > q)), d_median=float(np.median(v - q)))
    return res

if __name__ == '__main__':
    R = {}
    # C1: pipeline reproduces the recorded cash-0 MS1 rows
    C = std.contexts(); c1 = {}
    for bn, ref in (('real_ndx_86_14', 0.3052619999200501), ('real_spx_55_85', 0.10321809550001326)):
        c = C[bn]; B, bfn, bp, fs = std.s085(c); g, _ = std.engine(c, B, bfn, bp, fs, cspr=10.0)
        c1[bn] = dict(value=float(g[0]), ref=ref, ok=bool(abs(g[0] - ref) < 1e-6))
    R['C1'] = c1; print('C1', c1, flush=True)
    # C2: own builder on 1955-1985 vs MS1 real_spx_55_85 (calendar difference only)
    X2 = build(pd.Timestamp('1985-12-31'), 'A'); F2 = ov.flags_hist(X2); j = X2.index.searchsorted(pd.Timestamp('1955-01-03')) - W
    v2 = acct(X2, F2, j)[0]; R['C2'] = dict(own_builder_55_85=v2, ms1=0.10321809550001326, diff_pp=100 * (v2 - 0.10321809550001326),
                                            ok=bool(abs(v2 - 0.10321809550001326) <= 0.003)); print('C2', R['C2'], flush=True)
    del X2, F2
    # primary A, sensitivity B, recorded pipeline REC (no placebo)
    XA, FA, R['A'] = run_unit('A'); print('A', {k: v for k, v in R['A'].items() if k not in ('segments', 'alarm_on_by_year')}, flush=True)
    assert XA.index.max() <= END                                                                     # C4
    _, _, R['B'] = run_unit('B'); print('B', {k: v for k, v in R['B'].items() if k not in ('segments', 'alarm_on_by_year')}, flush=True)
    _, _, R['REC'] = run_unit('REC', placebo=False); print('REC', {k: R['REC'][k] for k in ('A', 'A_mdd', 'alarm_on_share')}, flush=True)
    # C3: 1x hold by hand on the scored rows
    r = XA['r'].values[W:]; e = np.cumprod(1 + (r - 0.002 / 252)); yrs = len(r) / 252
    fin = e[-1] * (1 - 0.003) - 0.22 * max(e[-1] * (1 - 0.003) - 1, 0)
    R['C3'] = dict(hand=float(fin ** (1 / yrs) - 1), engine=R['A']['HOLD1'], ok=bool(abs(fin ** (1 / yrs) - 1 - R['A']['HOLD1']) < 1e-4))
    print('C3', R['C3'], flush=True)
    # zone Z: from the first row with 378 rows of real TB3MS behind it
    zi = XA.index.searchsorted(CUT34) + 378
    zon = (FA['inv'] | FA['shock6m']).iloc[zi:]
    R['Z'] = dict(start=str(XA.index[zi].date()), alarm_on_share=float(zon.mean()))
    for nm, Fz in (('v1', FA), ('always', FA.assign(inv=True))):
        R['Z'][nm] = acct(XA, Fz, zi - W)[0]
    R['Z']['hold1x'] = float(std.hold(ov.Ctx(XA, FA, np.arange(zi - W, len(XA))[None, :]), 1)[0][0])
    print('Z', R['Z'], flush=True)
    R['rolling_A'] = rolling(XA, FA); print('rolling', R['rolling_A'], flush=True)
    # reference only: Fisher over AT2 five + Q1 Japan + LH1 A
    from scipy import stats
    at2 = json.load(open('/mnt/project-files/research/at2/results/at2_le2014.json'))
    ps = [at2[m]['p'] for m in ('UK', 'CA', 'AU', 'DE', 'FR')] + [0.76, R['A']['p']]
    R['ref_fisher_7'] = dict(ps=ps, fisher_p=float(stats.combine_pvalues(ps, method='fisher')[1]),
                             note='rate cycles are correlated across countries: overstated')
    final = R['A']['verdict'] if R['A']['verdict'] == R['B']['verdict'] else 'INCONCLUSIVE (proxy-dependent)'
    R['FINAL'] = final; print('FINAL', final, flush=True)
    json.dump(R, open(OUT, 'w'), indent=1); print('saved', OUT)
