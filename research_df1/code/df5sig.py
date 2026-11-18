"""DF5 path signals (PRECOMMIT_DF5.md section 3). Every value at t uses path data up to close t only.
REAL: before 1985-10-01 the NDX level used for signals is filled with S&P returns (assets untouched)."""
import numpy as np, pandas as pd
import df5lib as L
WARM = 300

def sma(lv, n):
    c = np.cumsum(np.c_[np.zeros(lv.shape[0]), lv], axis=1); out = np.full(lv.shape, np.nan)
    out[:, n - 1:] = (c[:, n:] - c[:, :-n]) / n
    return out

def gt(a, b):
    return np.where(np.isnan(b), False, a > b)

def kret(lv, k):
    out = np.full(lv.shape, np.nan); out[:, k:] = lv[:, k:] / lv[:, :-k] - 1; return out

def hyst(lv, s, b):
    """on above s*(1+b), off below s*(1-b), else keep; start = lv > s"""
    P, T = lv.shape; on = np.zeros((P, T), bool); st = np.zeros(P, bool)
    for t in range(T):
        st_ = np.where(np.isnan(s[:, t]), False, st)
        up = lv[:, t] > s[:, t] * (1 + b); dn = lv[:, t] < s[:, t] * (1 - b)
        st = np.where(np.isnan(s[:, t]), False, np.where(up, True, np.where(dn, False, st_)))
        on[:, t] = st
    return on

class Sig:
    def __init__(self, wname, base='NDX', pan=None):
        w = L.world(wname); m = w['m']; ii = w['ii']; S = w['S']
        self.w = w; self.ii = ii
        r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf']); self.rf = rf
        spx = np.nan_to_num(S['SPX'].values.astype(float)[ii]) - 0.02 / 252
        if base == 'NDX':
            rs = r.copy()
            if wname == 'REAL':
                d = S.index.values[ii[0]]; pre = d < np.datetime64('1985-10-01'); rs[0, pre] = spx[0, pre]
        elif base == 'SPX':
            rs = spx
        elif base == 'MIX':
            rs = 0.5 * r + 0.5 * spx
            if wname == 'REAL':
                d = S.index.values[ii[0]]; pre = d < np.datetime64('1985-10-01'); rs[0, pre] = spx[0, pre]
        self.r = rs
        self.lv = np.cumprod(1 + rs, axis=1)
        self.rfl = np.cumprod(1 + rf, axis=1)
        # credit spread path: first value + cumulative original-date daily changes
        cs = S['M_cs'].values.astype(float); dcs = np.r_[0.0, np.diff(cs)]; dcs = np.nan_to_num(dcs)
        csp = cs[ii[:, 0]][:, None] + np.cumsum(dcs[ii], axis=1) - dcs[ii[:, 0]][:, None]
        self.csp = csp
        y10 = S['M_y10'].values.astype(float); y3 = S['M_y3m'].values.astype(float)
        y3 = np.where(np.isnan(y3), S['M_rf'].values.astype(float) * 252 * 100, y3)
        self.slope = (y10 - y3)[ii]
        self._c = {}

    def c(self, key, fn):
        if key not in self._c: self._c[key] = fn()
        return self._c[key]

    def T(self, n): return self.c(('T', n), lambda: gt(self.lv, sma(self.lv, n)))
    def TH(self, b=0.02): return self.c(('TH', b), lambda: hyst(self.lv, sma(self.lv, 200), b))
    def M(self, k): return self.c(('M', k), lambda: np.where(np.isnan(kret(self.lv, k)), False, kret(self.lv, k) > kret(self.rfl, k)))
    def C0(self):
        def f():
            mu = L.roll_mean(self.csp, 252)
            return np.where(np.isnan(mu), False, self.csp <= mu + 1e-12)
        return self.c('C0', f)
    def D10(self):
        def f():
            hi = L.roll_max(self.lv, 252); dd = self.lv / hi - 1
            return np.where(dd <= -0.20, 0.0, np.where(dd <= -0.10, 0.5, 1.0))
        return self.c('D10', f)
    def dd252(self): return self.c('dd252', lambda: self.lv / L.roll_max(self.lv, 252) - 1)
    def vol(self, n): return self.c(('vol', n), lambda: L.roll_std(self.r, n) * np.sqrt(252))

    def mult(self, name):
        """signal multiplier m_t in [0, 1]"""
        if name == 'N': return np.ones(self.lv.shape)
        if name == 'T200': return self.T(200).astype(float)
        if name == 'T200H': return self.TH(0.02).astype(float)
        if name == 'M252': return self.M(252).astype(float)
        if name == 'C0': return self.C0().astype(float)
        if name == 'D10': return self.D10()
        if name == 'VOTE': return ((self.T(200).astype(int) + self.M(252).astype(int) + self.C0().astype(int)) >= 2).astype(float)
        if name == 'TE3': return (self.T(50).astype(float) + self.T(100) + self.T(200)) / 3.0
        if name == 'ME3': return (self.M(63).astype(float) + self.M(126) + self.M(252)) / 3.0
        if name == 'Y0T': return (self.T(200) & (self.slope > 0)).astype(float)
        raise KeyError(name)

    def lon(self, size):
        """size: ('F', L) fixed or ('V', sigma, w, Lmax) vol target"""
        if size[0] == 'F': return np.full(self.lv.shape, float(size[1]))
        _, s, wn, lm = size
        v = self.vol(wn)
        return np.where(np.isnan(v), 0.0, np.minimum(lm, s / np.maximum(v, 1e-9)))
