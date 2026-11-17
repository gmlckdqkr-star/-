"""Q1 alarm-truth test (see PREREG_Q1_ALARM_TRUTH.md): v1 unchanged on the Nikkei 225 with Japanese rates, <= 2014.
  python q1_japan.py checks      data checks only (dates, counts, yields); no account is computed
  python q1_japan.py run         the registered runs; writes results/q1.json
Run from /home/user (never with a working directory under /mnt/project-files/research)."""
import sys, os, json, time, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import ov, ce
D = '/mnt/project-files/research/q1_alarm/'
START, SUBS = '1981-01-01', (('1981-01-01', '1989-12-31'), ('1990-01-01', '2002-12-31'), ('2003-01-01', '2014-12-31'))
CASH0 = dict(cspr=10.0)

def frame():
    n = pd.read_csv(D + 'data/NIKKEI225_le2014.csv', parse_dates=['observation_date'], na_values='.').set_index('observation_date')['NIKKEI225'].astype(float).dropna()
    m = pd.read_csv(D + 'data/mof_jgb_le2014.csv', skiprows=1, na_values='-'); m.index = pd.to_datetime(m['Date'], format='%Y/%m/%d')
    y10d = m['10Y'].astype(float).where(m['10Y'].notna(), m['9Y'].astype(float)).dropna()
    cd = pd.read_csv(D + 'data/IR3TCD01JPM156N_le2014.csv', parse_dates=['observation_date'], na_values='.').set_index('observation_date')['IR3TCD01JPM156N'].astype(float).dropna()
    assert n.index.max() <= pd.Timestamp('2014-12-31') and m.index.max() <= pd.Timestamp('2014-12-31') and cd.index.max() <= pd.Timestamp('2014-12-31')
    n = n[n.diff() != 0]                                                  # carried-forward holiday rows (1981-86 in the source) are not trading days
    n = n[n.index >= y10d.index[0]]; idx = n.index
    y10 = y10d.reindex(idx, method='ffill').shift(1)                       # value of day t used from the next index row
    k = cd.copy(); k.index = k.index + pd.offsets.MonthBegin(1); y3m = k.reindex(idx, method='ffill')   # month m known from day 1 of m+1
    X = pd.DataFrame({'r': n.pct_change().fillna(0.0).values, 'rf': (y3m.fillna(0.0) / 100 / 252).values, 'y10': y10.values, 'y3m': y3m.values,
                      'cs': np.nan, 'vix': np.nan}, index=idx)
    return X, n, y10d, cd, m

def ctx(X, F, a, b=None):
    i0 = X.index.searchsorted(pd.Timestamp(a)) - ov.WARM; i1 = len(X) if b is None else X.index.searchsorted(pd.Timestamp(b), side='right')
    assert i0 >= 0
    return ov.Ctx(X, F, np.arange(i0, i1)[None, :]), i0, i1

def v1(c):
    B, bfn, bp, fs = std.s085(c); fin, E = std.engine(c, B, bfn, bp, fs, **CASH0)
    return float(fin[0]), float(ce.mdd(E)[0]), B

def checks():
    X, n, y10d, cd, m = frame(); i0 = X.index.searchsorted(pd.Timestamp(START))
    per = X.groupby(X.index.year).size(); z = (X['r'] == 0).groupby(X.index.year).sum(); print('zero-return rows left per year (max):', int(z.max())); print('index rows', len(X), 'from', X.index[0].date(), 'to', X.index[-1].date(), '| rows per year min', int(per.min()), 'max', int(per.max()), '| years below 240:', {int(y): int(v) for y, v in per.items() if v < 240})
    big = X['r'][X['r'].abs() > 0.12]; print('daily returns beyond 12 %:', [(str(d.date()), round(float(v), 4)) for d, v in big.items()])
    gap = pd.Series(X.index[1:] - X.index[:-1], index=X.index[1:]).dt.days; print('calendar gaps above 7 days:', [(str(d.date()), int(g)) for d, g in gap[gap > 7].items()])
    dy = y10d.diff().abs(); j = dy.idxmax(); print('largest one-row change of y10 %.3f pp on %s | 9Y to 10Y splice on %s, change %.3f pp' % (dy.max(), j.date(), m['10Y'].first_valid_index().date(), float(y10d.diff()[m['10Y'].first_valid_index()])))
    mm = pd.period_range('1979-05', '2014-12', freq='M'); miss = [str(p) for p in mm if p.to_timestamp() not in cd.index]; print('months without y3m 1979-05..2014-12:', miss)
    w = X.iloc[i0 - 378 - 126:i0]; print('first scored row', X.index[i0].date(), '| rows', len(X) - i0, '| first row with y3m', X['y3m'].first_valid_index().date(),
                                    '| NaN y10 / y3m in the look-back before the first scored row:', int(w['y10'].isna().sum()), int(w['y3m'].iloc[-378:].isna().sum()))
    assert int(w['y10'].isna().sum()) == 0 and int(w['y3m'].iloc[-378:].isna().sum()) == 0 and not miss
    print('y10 on the first scored row %.2f, y3m %.2f | y10 last row %.2f, y3m %.2f' % (X['y10'].iloc[i0], X['y3m'].iloc[i0], X['y10'].iloc[-1], X['y3m'].iloc[-1]))
    print('DATA CHECKS PASS')

def run():
    X, *_ = frame(); F = ov.flags_hist(X); out = dict(prereg_sha256=hashlib.sha256(open(os.path.dirname(os.path.abspath(__file__)) + '/PREREG_Q1_ALARM_TRUTH.md', 'rb').read()).hexdigest(),
                                                      script_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(), started=time.strftime('%FT%TZ', time.gmtime()))
    def variants(a, b=None):
        c, i0, i1 = ctx(X, F, a, b); r = {}
        cagr, dd, B = v1(c); r['A'] = dict(cagr=cagr, mdd=dd)
        Fa = F.copy(); Fa['inv'] = True; r['ALWAYS'] = dict(zip(('cagr', 'mdd'), v1(ctx(X, Fa, a, b)[0])[:2]))
        Fn = F.copy(); Fn['inv'] = False; Fn['shock6m'] = False; r['NEVER'] = dict(zip(('cagr', 'mdd'), v1(ctx(X, Fn, a, b)[0])[:2]))
        f, E = std.hold(c, 1); r['HOLD1'] = dict(cagr=float(f[0]), mdd=float(ce.mdd(E)[0]))
        f, E = std.engine(c, np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5, **CASH0); r['HOLD3'] = dict(cagr=float(f[0]), mdd=float(ce.mdd(E)[0]))
        s = slice(ov.WARM, None)
        r['rows'] = dict(scored=int(c.T - ov.WARM), inv_on=int(c.F['inv'][0, s].sum()), shock6m_on=int(c.F['shock6m'][0, s].sum()), v1_target_zero=int((B[0, s] == 0).sum()),
                         first=str(X.index[i0 + ov.WARM].date()), last=str(X.index[i1 - 1].date()))
        r['A_minus_ALWAYS'] = r['A']['cagr'] - r['ALWAYS']['cagr']; r['A_minus_NEVER'] = r['A']['cagr'] - r['NEVER']['cagr']
        return r, i0, i1
    out['full'], i0, i1 = variants(START); n = i1 - i0; pl = []
    for s in range(504, n - 504 + 1, 63):
        Fs = F.copy()
        for k in Fs.columns: v = Fs[k].values.copy(); v[i0:i1] = np.roll(v[i0:i1], s); Fs[k] = v
        pl.append(v1(ctx(X, Fs, START)[0])[0])
    pl = np.array(pl); a = out['full']['A']['cagr']; S = a - float(np.median(pl)); p = (1 + int((pl >= a).sum())) / (1 + len(pl))
    out['placebo'] = dict(n=len(pl), shifts='504 + 63 j rows', q05=float(np.quantile(pl, .05)), q25=float(np.quantile(pl, .25)), q50=float(np.median(pl)),
                          q75=float(np.quantile(pl, .75)), q95=float(np.quantile(pl, .95)), min=float(pl.min()), max=float(pl.max()))
    out['S'] = S; out['p'] = p
    out['verdict'] = 'ALARM TRANSFERS' if (S >= 0.03 and p <= 0.10) else ('ALARM DOES NOT TRANSFER' if (S <= 0 or p >= 0.50) else 'INCONCLUSIVE')
    out['sub'] = {'%s..%s' % (a_[:4], b_[:4]): variants(a_, b_)[0] for a_, b_ in SUBS}
    out['finished'] = time.strftime('%FT%TZ', time.gmtime()); os.makedirs(D + 'results', exist_ok=True)
    json.dump(out, open(D + 'results/q1.json', 'w'), indent=1); print(json.dumps(out, indent=1))

if __name__ == '__main__':
    {'checks': checks, 'run': run}[sys.argv[1]]()
