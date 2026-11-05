"""OV1-A signal library (frozen by PRECOMMIT.md sha256 70d8285c...). <=2014 only.
noise_star(): N* on the NDX calendar (drop off-calendar dates, lag 1 NDX day, ffill <= 5).
vix_star():   identical PIT treatment for the VIX control.
on_rows(A):   the on-rule along axis 1 of a (P,T) array (63/252/2.0/0.5/5, latest-argmax rule)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
CSV = '/mnt/project-files/research/ov1/lanes/OV1-A/data/noise_hpw_cut_le2014.csv'
END = pd.Timestamp('2014-12-31')
W_PK, W_BS, K_SP, K_RL, AGE = 63, 252, 2.0, 0.5, 5

def ndx_X():
    R, M = jp.calendar('1984-01-03', '2014-12-31'); return jp.mkX(R, M, 'NDX')

def _pit(s, cal):
    s = s[s.index <= END]
    return s.reindex(cal).shift(1).ffill(limit=5)        # off-calendar dates dropped by reindex; lag 1; ffill <= 5

def noise_star(cal):
    n = pd.read_csv(CSV, parse_dates=['Date']).set_index('Date')['Noise_bp']
    assert n.index.max() <= END and n.index.is_unique
    return _pit(n.astype(float), cal)

def vix_star(X):
    return _pit(X['vix'].astype(float), X.index)

def on_rows(A):
    """A: (P,T) float array (NaN = no info). Returns (P,T) bool on, rolling along axis 1."""
    df = pd.DataFrame(np.asarray(A, float).T)                   # (T,P): rolling over rows = time
    base = df.rolling(W_BS, min_periods=W_BS).median()
    peak = df.rolling(W_PK, min_periods=W_PK).max()
    rec = df.rolling(AGE, min_periods=AGE).max()                 # max over t-4..t
    full = df.notna().rolling(W_BS, min_periods=W_BS).sum() >= W_BS
    x = df
    spike = peak >= K_SP * base
    relief = (x <= base + K_RL * (peak - base)) & (rec < peak)  # latest argmax k_t: t-k_t>=5 <=> max(t-4..t) < peak
    on = spike & relief & full & x.notna() & base.notna() & peak.notna()
    return on.values.T.astype(bool)

def on_series(s):
    return pd.Series(on_rows(s.values[None, :])[0], index=s.index)
