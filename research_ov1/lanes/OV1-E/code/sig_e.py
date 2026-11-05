"""OV1-E signal library (TED funding-stress CUT). <=2014 data only. No returns are read here.
TED*(t)  = DED3*(t) - DTB3*(t), where X*(t) = the latest FRED observation of X dated STRICTLY BEFORE trading day t
           (one-day publication lag: a value dated d is first used at the close of the first trading day after d).
           Each series is forward-filled separately on its own observation dates (no ffill limit), then differenced.
x(t)     = TED*(t) - TED*(t-63)            (63 positions back along the row: master trading calendar, or one MS1 path row)
q90(t)   = numpy.quantile(x[t-1260 .. t-1], 0.90, method='linear')   (1260 values strictly before t, all must be defined)
ON(t)    = x(t) defined AND q90(t) defined AND x(t) > q90(t)   (strict).  Undefined -> ON False (fallback = v1).
Overlay  : B_new(t) = 1 if v1_B(t) == 3 and ON(t), else v1_B(t).
Master trading calendar = jp.calendar('1928-01-03', '2014-12-31') index (one US calendar shared by the SPX and NDX frames)."""
import sys, numpy as np, pandas as pd
D = '/mnt/project-files/research/ov1/lanes/OV1-E/data/'
CUT = pd.Timestamp('2014-12-31')
H, W, Q = 63, 1260, 0.90

def read_fred(sid):
    s = pd.read_csv(D + 'cut_%s_le2014.csv' % sid)
    s.columns = ['date', 'v']; s['date'] = pd.to_datetime(s['date']); s = s[s['date'] <= CUT]
    v = pd.to_numeric(s['v'], errors='coerce')
    out = pd.Series(v.values, index=s['date'].values).sort_index().dropna()
    assert out.index.is_unique and out.index.max() <= CUT
    return out

def master_cal():
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
    R, M = jp.calendar('1928-01-03', '2014-12-31'); return R.index

def lag1_onto(s, cal):
    """value at trading day t = last observation dated strictly before t (calendar date)."""
    pos = np.searchsorted(s.index.values, cal.values, side='left') - 1     # last obs with date < t
    v = np.where(pos >= 0, s.values[np.maximum(pos, 0)], np.nan)
    return pd.Series(v, index=cal)

def ted_star(cal=None):
    cal = master_cal() if cal is None else cal
    ded = read_fred('DED3'); dtb = read_fred('DTB3')
    a = lag1_onto(ded, cal); b = lag1_onto(dtb, cal)
    return a - b                                                         # NaN where DED3 has not started (before 1971-01-05)

def on_rows(A):
    """A: (P,T) float array of TED* along each row (NaN = no info). Returns ON (P,T) bool, x (P,T), q90 (P,T)."""
    A = np.asarray(A, float); P, T = A.shape
    x = np.full((P, T), np.nan); x[:, H:] = A[:, H:] - A[:, :-H]
    q = np.full((P, T), np.nan)
    for i in range(P):
        xi = x[i]
        if T <= W: continue
        win = np.lib.stride_tricks.sliding_window_view(xi[:-1], W)      # win[k] = xi[k .. k+W-1] -> threshold for t = k+W
        ok = ~np.isnan(win).any(axis=1)
        qq = np.full(win.shape[0], np.nan)
        if ok.any(): qq[ok] = np.quantile(win[ok], Q, axis=1, method='linear')
        q[i, W:] = qq
    on = (~np.isnan(x)) & (~np.isnan(q)) & (x > q)
    return on, x, q

def on_series(s):
    on, x, q = on_rows(s.values[None, :])
    return pd.Series(on[0], index=s.index), pd.Series(x[0], index=s.index), pd.Series(q[0], index=s.index)

def overlay(B, ON):
    B = np.asarray(B, float).copy(); B[(B == 3) & np.asarray(ON, bool)] = 1.0; return B
