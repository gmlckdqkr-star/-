"""NP1-KF definitions (frozen before the first outcome run; sha256 in code/CODE_FREEZE.sha256). <= 2014 only.
PRECOMMIT_KF.md fixes the rule; every point it leaves open is fixed HERE, before any result.

Signal source: data/kospi_foreign_le2014.csv (ECOS 802Y001: 0030000 KOSPI foreign net buying, 0030000 unit 억원; 0183000 KOSPI market cap, 억원),
KR trading days 2003-01-02..2014-12-30.
  daily normalized flow  f_d = fnet_d / mcap_d   (same KR date d; both known after the KR close)
  cumulative level       C_d = cumsum(f_d)        (the 'level' that ov1lib.path_series rebuilds along a path by cumulating its own changes)
Timing (point in time): KR date d closes 15:30 KST = before the US open of the same calendar date. To stay conservative the value of KR
  date d is used from US date d+1 on (index shifted +1 calendar day, then ffill onto US trading days). The MS1 engine adds its own
  2-day execution delay on top (decision at US close t, trade at t+2).
On every basis the (P,T) array of C is built two ways (ov1lib): 'path' = rebuilt along the resampled path (HEADLINE),
  'glued' = value of the source date (upper bound; equal to path on real NDX).
  F_n(t) = C(t) - C(t-n)  (n US rows along the path; NaN if either end is NaN)
  z_n(t) = (F_n(t) - mean) / std over the previous 504 rows t-504..t-1 of F_n with >= 189 finite values, else NaN (no signal)
Variants (N = 4):
  KF20C  CUT  ON_t if z_20 <= -1.5 at any close in t-20..t  -> B' = min(B, 1)
  KF60C  CUT  ON_t if z_60 <= -1.5 at any close in t-20..t  -> B' = min(B, 1)
  KF20A  ADD  ON_t if z_20 >= +1.5 at any close in t-20..t  -> B' = 3 where B == 1 (never from 0 = crisis-gate cash)
  KF60A  ADD  ON_t if z_60 >= +1.5 at any close in t-20..t  -> B' = 3 where B == 1
  Brake = v1's (av23s .85, fstep .1) unchanged. NaN z -> no trigger -> B' = B (v1). Before 2003 / S&P bases: no data -> equal to v1."""
import numpy as np, pandas as pd
LANE = '/mnt/project-files/research/np1/'
CSV = LANE + 'data/kospi_foreign_le2014.csv'
END = pd.Timestamp('2014-12-31')
VARIANTS = {'KF20C': dict(n=20, side='cut'), 'KF60C': dict(n=60, side='cut'),
            'KF20A': dict(n=20, side='add'), 'KF60A': dict(n=60, side='add')}
ZWIN, ZMIN, ZTH, HOLD = 504, 189, 1.5, 21

def level_series():
    """pandas Series C indexed by (KR date + 1 calendar day); rows <= 2014-12-31 only."""
    d = pd.read_csv(CSV, parse_dates=['krdate']).set_index('krdate'); assert d.index.max() <= END and d.index.is_unique
    f = (d['fnet_eok'] / d['mcap_eok']).astype(float); assert np.isfinite(f).all()
    C = f.cumsum(); C.index = C.index + pd.Timedelta(days=1)
    return C[C.index <= END].rename('C')

def diff_n(C, n):
    out = np.full(C.shape, np.nan); out[:, n:] = C[:, n:] - C[:, :-n]; return out

def zscore(F, win=ZWIN, mn=ZMIN):
    """trailing z along axis 1 using rows t-win..t-1 only (no look-ahead); NaN-aware via cumulative sums."""
    P, T = F.shape; ok = np.isfinite(F); x = np.where(ok, F, 0.0)
    c1 = np.c_[np.zeros((P, 1)), np.cumsum(x, 1)]; c2 = np.c_[np.zeros((P, 1)), np.cumsum(x * x, 1)]; cn = np.c_[np.zeros((P, 1)), np.cumsum(ok, 1)]
    hi = np.arange(T); lo = np.maximum(hi - win, 0)            # window = rows lo..t-1
    n = cn[:, hi] - cn[:, lo]; s1 = c1[:, hi] - c1[:, lo]; s2 = c2[:, hi] - c2[:, lo]
    with np.errstate(divide='ignore', invalid='ignore'):
        m = s1 / n; v = (s2 - n * m * m) / (n - 1); z = (F - m) / np.sqrt(v)
    z[(n < mn) | ~ok | ~(v > 0)] = np.nan
    return z

def _roll_any(a, k):
    a = np.asarray(a, bool); c = np.cumsum(np.c_[np.zeros((a.shape[0], 1), int), a.astype(int)], axis=1)
    lo = np.maximum(np.arange(a.shape[1]) - k + 1, 0); hi = np.arange(a.shape[1]) + 1
    return (c[:, hi] - c[:, lo]) > 0

def on_window(C, var):
    k = VARIANTS[var]; z = zscore(diff_n(C, k['n']))
    trig = (z <= -ZTH) if k['side'] == 'cut' else (z >= ZTH)
    trig = np.where(np.isfinite(z), trig, False)
    return _roll_any(trig, HOLD), trig

def overlay(B, on, var):
    if VARIANTS[var]['side'] == 'cut': return np.where(on, np.minimum(B, 1.0), B)
    return np.where(on & (B == 1.0), 3.0, B)
