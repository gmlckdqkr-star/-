"""CAPIT definitions (frozen before the first kill-test run; sha256 in code/CODE_FREEZE.sha256). <= 2014 only.
PRECOMMIT.md (sha256 ec06110c92bf...) section 4 fixes the rule; the points it leaves open are fixed HERE, before any result:
  RSI(14)      Wilder's RSI on daily closes: change d_t = p_t - p_{t-1}; first average = simple mean of the first 14 gains / losses,
               then avg_t = (13*avg_{t-1} + x_t)/14; RSI = 100 - 100/(1 + avgGain/avgLoss); avgLoss == 0 and avgGain > 0 -> 100;
               both 0 (flat price, e.g. before the index exists) -> NaN (no trigger). p = c.lvl (path price) on every basis.
  volume ratio VR_t = V_t / median(V_{t-60} .. V_{t-1}) on the SOURCE series' own trading days (lane data/ndx_close_volume_le2014.csv,
               volume valid = finite and > 0); needs 60 earlier rows with >= 40 valid values, else NaN (no trigger).
               It is a property of the source DATE; on resampled paths it is GLUED from the source date of each path day (L.gather).
  CAP1 trigger at close t: RSI_t <= 30 AND VR_t >= 2.0.                                   Effect window W = 42.
  CAP2 trigger at close t: min(RSI_{t-2..t}) <= 30 AND max(VR_{t-2..t}) >= 2.5 (path days). Effect window W = 63.
  ON_t = a trigger at any close in t-W+1 .. t  (the target decided at the trigger close and at the next W-1 closes; the engine's
         2-day execution delay applies as for every v1 decision).
  Overlay target: B' = 3 where ON and v1 base target B < 3, else B. Brake = v1's (av23s .85, fstep .1) unchanged.
  No data (NaN RSI or NaN VR, e.g. S&P 1955-85 bases) -> no trigger -> B' = B (v1).  Sentinel -1 = 'no volume info' through L.gather."""
import numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
CSV = LANE + 'data/ndx_close_volume_le2014.csv'
END = pd.Timestamp('2014-12-31')
VARIANTS = {'CAP1': dict(rsi_max=30.0, vr_min=2.0, look=1, W=42), 'CAP2': dict(rsi_max=30.0, vr_min=2.5, look=3, W=63)}

def volume_ratio():
    """pandas Series by source date: V_t / median(previous 60 rows), NaN where undefined. Rows <= 2014-12-31 only."""
    d = pd.read_csv(CSV, parse_dates=['date']).set_index('date'); assert d.index.max() <= END and d.index.is_unique
    v = d['volume'].astype(float).where(lambda s: np.isfinite(s) & (s > 0))
    med = v.shift(1).rolling(60, min_periods=40).median()
    med[:60] = np.nan                                   # needs 60 earlier rows
    return (v / med).rename('vr')

def vr_for_gather(cal_union):
    """series on a calendar with sentinel -1 where there is no ratio (so that L.gather's ffill cannot copy a spike forward)."""
    return volume_ratio().reindex(cal_union).fillna(-1.0)

def rsi14(lvl, n=14):
    """Wilder RSI along axis 1 of a (P,T) price array. NaN until n changes exist or while the price has been flat."""
    lvl = np.asarray(lvl, float); P, T = lvl.shape
    d = np.diff(lvl, axis=1); g = np.maximum(d, 0.0); l = np.maximum(-d, 0.0)
    out = np.full((P, T), np.nan)
    if T <= n: return out
    ag = g[:, :n].mean(1); al = l[:, :n].mean(1)
    def val(ag, al):
        with np.errstate(divide='ignore', invalid='ignore'):
            r = 100.0 - 100.0 / (1.0 + ag / al)
        r = np.where(al == 0, np.where(ag > 0, 100.0, np.nan), r); return r
    out[:, n] = val(ag, al)
    for t in range(n + 1, T):
        ag = (ag * (n - 1) + g[:, t - 1]) / n; al = (al * (n - 1) + l[:, t - 1]) / n
        out[:, t] = val(ag, al)
    return out

def _roll_any(a, k):
    """True at t if a is True at any of t-k+1..t (axis 1)."""
    a = np.asarray(a, bool); c = np.cumsum(np.c_[np.zeros((a.shape[0], 1), int), a.astype(int)], axis=1)
    lo = np.maximum(np.arange(a.shape[1]) - k + 1, 0); hi = np.arange(a.shape[1]) + 1
    return (c[:, hi] - c[:, lo]) > 0

def trigger(rsi, vr, var):
    """(P,T) bool trigger at close t. vr: (P,T) with NaN or negative = no info."""
    k = VARIANTS[var]; rsi = np.asarray(rsi, float); vr = np.asarray(vr, float)
    lo = np.isfinite(rsi) & (rsi <= k['rsi_max']); hi = np.isfinite(vr) & (vr >= k['vr_min'])
    if k['look'] == 1: return lo & hi
    return _roll_any(lo, k['look']) & _roll_any(hi, k['look'])

def on_window(trig, var):
    return _roll_any(trig, VARIANTS[var]['W'])

def overlay(B, on):
    return np.where(on & (B < 3.0), 3.0, B)
