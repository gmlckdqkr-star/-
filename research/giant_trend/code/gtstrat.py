"""Giant rules (PRECOMMIT_GT.md section 4). Each builder returns dec list (len T). Index t = month end t."""
import numpy as np, pandas as pd

class Ctx:
    def __init__(self, D):
        self.D = D; self.idx = D['ind'].index; self.T = len(self.idx)
        self.names = list(D['ind'].columns)
        self.r = D['ind'].values                      # T x 17
        self.I = np.cumprod(1 + np.nan_to_num(self.r), axis=0)
        self.mI = np.cumprod(1 + D['mkt'].fillna(0).values)
        self.rf = D['rf'].values
        self.mup = np.array([t >= 9 and self.mI[t] > self.mI[t - 9:t + 1].mean() for t in range(self.T)])
        self.fac = D['fac']
    def RS(self, k, t):
        return self.I[t] / self.I[t - k] - 1 if t >= k else None
    def t_of(self, s): return self.idx.get_loc(pd.Period(s, 'M'))

def _emit(dec, t, tgt, prev):
    """emit ('w', tgt) only when the target set/weights change"""
    if prev is None or prev != tgt: dec[t] = ('w', dict(tgt)); return tgt
    return prev

def warm(c, dec, t_start):
    dec[0] = ('w', {'MKT': 1.0})

# ---- trend Buffett / Munger -------------------------------------------------
def buf_t(c, score='rs60', review='annual', top=3, keep_rank=6, every=60):
    dec = [None] * c.T; warm(c, dec, 0); held = []; last_review = None
    for t in range(60, c.T):
        if c.idx[t].month != 12: continue
        if review == 'every' and last_review is not None and t - last_review < every: continue
        rs = c.RS(60, t)
        if score == 'rs60/vol':
            v = np.nanstd(c.r[t - 59:t + 1], axis=0); sc = rs / np.where(v > 0, v, np.nan)
        else: sc = rs
        order = [c.names[i] for i in np.argsort(-np.nan_to_num(sc, nan=-1e9))]
        if not held:
            held = order[:top]; dec[t] = ('w', {a: 1.0 / top for a in held}); last_review = t; continue
        if review == 'every':
            keep = [a for a in held if a in order[:top]]
        else:
            keep = [a for a in held if a in order[:keep_rank]]
        new = [a for a in order if a not in keep][:top - len(keep)]
        if set(keep) != set(held):
            # sold names leave (incl. any MKT warm-up weight), freed value split over new
            dec[t] = ('swap', (keep, new)); held = keep + new
        last_review = t
    # first decision replaces warm-up MKT fully: handled because 'w' at first review
    return dec

# ---- simple holds / factor mixes -------------------------------------------
def hold_mix(c, mix, start=None):
    dec = [None] * c.T; warm(c, dec, 0)
    t0 = 0 if start is None else c.t_of(start)
    # monthly rebalance for multi-asset mixes, single asset just held
    for t in range(t0, c.T):
        if t == t0 or len(mix) > 1: dec[t] = ('w', dict(mix))
    return dec

def gra_t(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    h = c.D['hml'].fillna(0).values
    for t in range(12, c.T):
        v = np.prod(1 + h[t - 11:t + 1]) - 1
        prev = _emit(dec, t, {'BIG_HiBM': 1.0} if v > 0 else {'BIG_LoBM': 1.0}, prev)
    return dec

def gra_c(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    cape = c.D['sh']['CAPE'].values; med = c.D['sh']['CAPE_med240'].values
    for t in range(c.T):
        if np.isnan(cape[t]) or np.isnan(med[t]): continue
        prev = _emit(dec, t, {'MKT': 1.0} if cape[t] <= med[t] else {'MKT': .5, 'CASH': .5}, prev)
    return dec

# ---- O'Neil, Druckenmiller, Soros -------------------------------------------
def one_t(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    for t in range(12, c.T):
        if not c.mup[t]: tgt = {'CASH': 1.0}
        else:
            hi = c.I[t - 11:t + 1].max(axis=0); ok = c.I[t] >= 0.95 * hi
            rs = c.RS(6, t); cand = [i for i in np.argsort(-rs) if ok[i]][:2]
            tgt = {c.names[i]: 1.0 / len(cand) for i in cand} if cand else {'MKT': 1.0}
        prev = _emit(dec, t, tgt, prev)
    return dec

def dru_t(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    y = c.D['sh']['GS10'].values
    for t in range(12, c.T):
        loose = y[t] < np.nanmean(y[t - 11:t + 1])
        if loose and c.mup[t]: tgt = {c.names[int(np.argmax(c.RS(6, t)))]: 1.0}
        elif loose or c.mup[t]: tgt = {'MKT': 1.0}
        else: tgt = {'CASH': 1.0}
        prev = _emit(dec, t, tgt, prev)
    return dec

def sor_t(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    for t in range(15, c.T):
        sma = c.I[t - 9:t + 1].mean(axis=0); up = c.I[t] > sma; rs12 = c.RS(12, t)
        acc = c.RS(6, t) - (c.I[t - 6] / c.I[t - 12] - 1)
        cand = [i for i in np.argsort(-acc) if up[i] and rs12[i] > 0][:2]
        tgt = {c.names[i]: 1.0 / len(cand) for i in cand} if cand else {'CASH': 1.0}
        prev = _emit(dec, t, tgt, prev)
    return dec

# ---- Dalio -------------------------------------------------------------------
def _quad(c):
    g = c.D['sh']['grow_up'].values; p = c.D['sh']['infl_up'].values
    q = np.where(np.isnan(g) | np.isnan(p), -1, (np.nan_to_num(g) * 2 + np.nan_to_num(p))).astype(int)
    return q

def dal_q(c, frozen_end=None, top=3, minn=36):
    dec = [None] * c.T; warm(c, dec, 0); prev = None; q = _quad(c)
    ex = np.nan_to_num(c.r) - c.rf[:, None]
    if frozen_end is not None:
        te = c.t_of(frozen_end); fmap = {}
        for k in range(4):
            ss = [s for s in range(c.T - 1) if q[s] == k and s + 1 <= te]
            fmap[k] = [c.names[i] for i in np.argsort(-ex[[s + 1 for s in ss]].mean(axis=0))[:top]] if len(ss) >= minn else None
    for t in range(1, c.T):
        if q[t] < 0: continue
        if frozen_end is not None: sel = fmap[q[t]]
        else:
            ss = [s for s in range(t) if q[s] == q[t]]          # pairs (state s, return s+1), s+1 <= t
            sel = [c.names[i] for i in np.argsort(-ex[[s + 1 for s in ss]].mean(axis=0))[:top]] if len(ss) >= minn else None
        tgt = {a: 1.0 / len(sel) for a in sel} if sel else {'MKT': 1.0}
        prev = _emit(dec, t, tgt, prev)
    return dec

def dal_rp(c):
    dec = [None] * c.T; warm(c, dec, 0)
    m = c.D['mkt'].values; b = c.D['bond'].values
    for t in range(37, c.T):
        vm = np.nanstd(m[t - 35:t + 1]); vb = np.nanstd(b[t - 35:t + 1])
        wm = (1 / vm) / (1 / vm + 1 / vb)
        dec[t] = ('w', {'MKT': wm, 'BOND10': 1 - wm})
    return dec

# ---- Templeton -----------------------------------------------------------------
def tem(c, need_secular=False):
    dec = [None] * c.T; warm(c, dec, 0); slots = [None, None, None]; prev = None
    t0 = 120 if need_secular else 60
    for t in range(t0, c.T):
        changed = False
        for j in range(3):
            if slots[j] is not None and t - slots[j][1] >= 36: slots[j] = None; changed = True
        held = {s[0] for s in slots if s is not None and s[0] != 'MKT'}
        dd = c.I[t] / c.I[t - 59:t + 1].max(axis=0) - 1; rs3 = c.RS(3, t)
        ok = rs3 > 0
        if need_secular: ok &= c.RS(120, t) > 0
        cand = [c.names[i] for i in np.argsort(dd) if ok[i] and c.names[i] not in held]
        for j in range(3):
            if slots[j] is None:
                a = cand.pop(0) if cand else 'MKT'; slots[j] = (a, t); changed = True
        if changed or prev is None:
            tgt = {}
            for s in slots: tgt[s[0]] = tgt.get(s[0], 0.0) + 1 / 3
            dec[t] = ('w', tgt); prev = tgt
    return dec

# ---- Marks, Tudor, Thorp ----------------------------------------------------------
def mar_t(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None; s = c.D['spread'].values
    for t in range(120, c.T):
        med = np.nanmedian(s[t - 119:t + 1])
        if s[t] > med and s[t] < s[t - 3]: tgt = {'MKT': 1.0}
        elif s[t] < med and s[t] > s[t - 3]: tgt = {'CASH': 1.0}
        else: tgt = {'MKT': 1.0}
        prev = _emit(dec, t, tgt, prev)
    return dec

def tud_b(c):
    dec = [None] * c.T; warm(c, dec, 0); prev = None
    for t in range(9, c.T): prev = _emit(dec, t, {'MKT': 1.0} if c.mup[t] else {'CASH': 1.0}, prev)
    return dec

def lag(dec, k=1):
    """stress: every decision takes effect k months later"""
    return [None] * k + dec[:-k] if k else dec
