"""OV1-F signal construction (yen carry-unwind CUT). <=2014 data only.
Input: FRED DEXJPUS (JPY per USD, H.10 noon buying rate NY), file data/cut_DEXJPUS_le2014.csv (rows <= 2014-12-31 only).
Point-in-time: value dated d is usable from the first trading day AFTER d (index d + 1 calendar day, then forward-fill
onto the trading calendar; union + ffill exactly like ov1lib._onto). Holidays (empty values) are dropped before mapping.
On any 1-D row lx of log(DEXJPUS) on trading days (master calendar for real bases, each path row for MS1 path):
  yen21(t) = -(lx(t) - lx(t-21))                         positive = yen appreciation; NaN if either end is NaN
  thr(t)   = numpy-'linear' 95th percentile of yen21(t-756 .. t-1) (756 values strictly before t); NaN unless all 756 defined
  fire(t)  = yen21(t) > thr(t)  (strict; False where either is NaN)
  ON(t)    = fire(t-20) or ... or fire(t)                 (a fire keeps ON for 21 trading days incl. the fire day)
Overlay (CUT): B_new = 1 where v1_B == 3 and ON, else v1_B."""
import numpy as np, pandas as pd
from numba import njit
LANE = '/mnt/project-files/research/ov1/lanes/OV1-F/'
D = LANE + 'data/'
CUT = pd.Timestamp('2014-12-31')
H, W, Q, HOLD = 21, 756, 0.95, 21

def raw():
    s = pd.read_csv(D + 'cut_DEXJPUS_le2014.csv'); s.columns = ['date', 'v']
    s['date'] = pd.to_datetime(s['date']); s = s[s['date'] <= CUT]
    v = pd.to_numeric(s['v'], errors='coerce')
    return pd.Series(v.values, index=s['date'].values).sort_index()

def log_avail():
    """log(DEXJPUS) indexed by availability date d + 1 calendar day (holidays dropped)."""
    s = raw().dropna(); s = s[s > 0]
    return pd.Series(np.log(s.values), index=s.index + pd.Timedelta(days=1))

def master_cal():
    import jp
    R, M = jp.calendar('1928-01-03', '2014-12-31'); return R.index

def onto(series, cal):
    s = pd.Series(series).sort_index(); s = s[s.index <= CUT]
    return s.reindex(cal.union(s.index)).ffill().reindex(cal).values.astype(float)

@njit(cache=False)
def _thr_row(y, W, q):
    T = y.shape[0]; thr = np.full(T, np.nan); buf = np.empty(W + 1); n = 0; nnan = 0
    pos = q * (W - 1); lo = int(np.floor(pos)); fr = pos - lo
    for t in range(T):
        if t >= 1:                         # add y[t-1]
            v = y[t - 1]
            if np.isnan(v): nnan += 1
            else:
                k = np.searchsorted(buf[:n], v)
                for j in range(n, k, -1): buf[j] = buf[j - 1]
                buf[k] = v; n += 1
        if t - W - 1 >= 0:                 # remove y[t-W-1] -> window = y[t-W .. t-1]
            v = y[t - W - 1]
            if np.isnan(v): nnan -= 1
            else:
                k = np.searchsorted(buf[:n], v)
                for j in range(k, n - 1): buf[j] = buf[j + 1]
                n -= 1
        if t >= W and nnan == 0 and n == W:
            thr[t] = buf[lo] + fr * (buf[lo + 1] - buf[lo]) if lo + 1 < W else buf[lo]
    return thr

def signal_rows(lx):
    """lx: (P,T) log level along each row. Returns dict of (P,T) arrays: y21, thr, fire, on."""
    lx = np.atleast_2d(np.asarray(lx, dtype=np.float64)); P, T = lx.shape
    y = np.full((P, T), np.nan); y[:, H:] = -(lx[:, H:] - lx[:, :-H])
    thr = np.empty((P, T))
    for i in range(P): thr[i] = _thr_row(np.ascontiguousarray(y[i]), W, Q)
    ok = ~np.isnan(y) & ~np.isnan(thr)
    fire = np.zeros((P, T), bool); fire[ok] = y[ok] > thr[ok]
    cs = np.cumsum(np.c_[np.zeros((P, 1), int), fire.astype(int)], axis=1)        # cs[:, t+1] = fires in 0..t
    lo = np.maximum(np.arange(T) - (HOLD - 1), 0)
    on = (cs[:, 1:] - cs[:, lo]) > 0                                               # any fire in t-20..t
    return dict(y21=y, thr=thr, fire=fire, on=on, valid=~np.isnan(thr) & ~np.isnan(y))

def master_signal():
    """Signal on the master US trading calendar 1928-2014 (DEXJPUS covers from 1971). pd.DataFrame by date."""
    cal = master_cal(); lx = onto(log_avail(), cal); S = signal_rows(lx[None, :])
    return pd.DataFrame({k: v[0] for k, v in S.items()} | dict(lx=lx), index=cal)
