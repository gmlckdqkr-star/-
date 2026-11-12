"""AT2 runs (PRECOMMIT_AT2.md + ADDENDUM 1): v1 unchanged on 6 foreign indices with own OECD rates; placebo = circular flag shift."""
import os, sys, json, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/nbc'
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import ov, mkt
DD = '/mnt/project-files/research/at2/data/'; OUT = '/mnt/project-files/research/at2/results/at2_le2014.json'
CC = {'UK': 'GB', 'CA': 'CA', 'AU': 'AU', 'DE': 'DE', 'FR': 'FR', 'CH': 'CH'}
def monthly(sid, idx):
    f = pd.read_csv(DD + sid + '_le2014.csv', parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0].dropna()
    f.index = f.index + pd.offsets.MonthBegin(1)            # value of month m usable from the first row of month m+1
    return f.reindex(idx.union(f.index)).ffill().reindex(idx)
def build(m):
    s = pd.read_csv(DD + '%s_index_le2014.csv' % m, parse_dates=['date']).set_index('date')['close']
    X = pd.DataFrame(index=s.index); X['r'] = s.pct_change().fillna(0.0)
    X['y3m'] = monthly('IR3TIB01%sM156N' % CC[m], X.index); X['y10'] = monthly('IRLTLT01%sM156N' % CC[m], X.index)
    X['rf'] = X['y3m'] / 100 / 252; X['cs'] = 0.0; X['vix'] = np.nan
    ok = X[['y3m', 'y10']].notna().all(axis=1)
    first_rate = ok.idxmax() if ok.any() else None
    X[['y3m', 'y10', 'rf']] = X[['y3m', 'y10', 'rf']].fillna(0.0)
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    pos_rate = X.index.get_loc(first_rate)
    i0 = max(0, pos_rate + 378 - ov.WARM)                    # first scored row must have 378 real-rate rows behind it
    return X, i0
def acct(X, F, i0, flags=None):
    c = ov.Ctx(X, F if flags is None else flags, np.arange(i0, len(X))[None, :])
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    return float(cg[0]), float((E[0] / np.maximum.accumulate(E[0]) - 1).min())
res = {}
for m in ['UK', 'CA', 'AU', 'DE', 'FR', 'CH']:
    X, i0 = build(m); F = ov.flags_hist(X); n = len(X)
    a, mdd = acct(X, F, i0)
    rows = np.arange(i0, n); N = len(rows); pl = []
    s = 504
    while s <= N - 504:
        Fs = F.copy(); Fs.iloc[rows] = F.iloc[np.roll(rows, s)].values; pl.append(acct(X, Fs, i0)[0]); s += 63
    pl = np.array(pl)
    Fa = F.copy(); Fa['inv'] = True; Fn = F.copy(); Fn['inv'] = False; Fn['shock6m'] = False
    h1 = float(std.hold(ov.Ctx(X, F, np.arange(i0, n)[None, :]), 1)[0][0])
    S = a - float(np.median(pl)); p = (1 + int((pl >= a).sum())) / (1 + len(pl))
    verdict = 'TRANSFERS' if (S >= 0.03 and p <= 0.10) else ('DOES NOT TRANSFER' if (S <= 0 or p >= 0.5) else 'INCONCLUSIVE')
    res[m] = dict(scored_from=str(X.index[i0 + ov.WARM].date()), rows=N - ov.WARM, A=a, A_mdd=mdd, placebo_med=float(np.median(pl)), n_placebo=len(pl), S=S, p=p,
                  verdict=verdict, ALWAYS=acct(X, Fa, i0)[0], NEVER=acct(X, Fn, i0)[0], HOLD1=h1,
                  alarm_on_share=float((F['inv'] | F['shock6m']).iloc[i0 + ov.WARM:].mean()))
    print(m, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res[m].items()}), flush=True)
from scipy import stats
P5 = ['UK', 'CA', 'AU', 'DE', 'FR']
mS = float(np.mean([res[m]['S'] for m in P5])); fp = float(stats.combine_pvalues([res[m]['p'] for m in P5], method='fisher')[1])
res['POOLED5'] = dict(mean_S=mS, fisher_p=fp, verdict='TRANSFERS' if (mS >= 0.02 and fp <= 0.10) else ('DOES NOT TRANSFER' if (mS <= 0 or fp >= 0.5) else 'INCONCLUSIVE'))
mS7 = (sum(res[m]['S'] for m in P5) - 0.006) / 6; fp7 = float(stats.combine_pvalues([res[m]['p'] for m in P5] + [0.76], method='fisher')[1])
res['POOLED6_with_JP_Q1'] = dict(mean_S=mS7, fisher_p=fp7)
print('POOLED5', res['POOLED5'], 'with JP', res['POOLED6_with_JP_Q1'])
json.dump(res, open(OUT, 'w'), indent=1)
