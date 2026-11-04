"""Evaluate an arbitrary daily DECISION series (product code decided at close t: 0=3x 1=2x 2=1x 3=cash 4=-1x) with the
exact BT1/M1 engine conventions (2-day delay, 0.3%/side on non-cash legs, MS1 product costs).
  ev = Evaluator()
  ev.era_dates('spx' | 'ndx')                 -> DatetimeIndex of each era's rows (spx 1954-1985, ndx 1985-2014)
  D, S = ev.discovery(dec_spx, dec_ndx)       -> 540 monthly log-diffs vs 1x (S&P 1955-85 + NDX 1986-99) and stats
  ev.confirm(dec_ndx)                         -> dict: NDX 2000-2014 annualized log advantage vs 1x and vs s0.85
  ev.ms1(dec_spx, dec_ndx, label)             -> MS1 rows (real paths after tax) + representative conversion
dec arrays must be int arrays aligned with era_dates(e); use 2 (1x) where the rule has no value."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, m1_search as SE, m1_confirm as CF, m1_ms1 as MM
from numba import njit


@njit(cache=True)
def _g(LX, dec, CC):
    t1 = dec.shape[0]; g = np.zeros(t1)
    for t in range(t1):
        p = dec[t - 3] if t >= 3 else 2
        pn = dec[t - 2] if t >= 2 else 2
        lg = LX[p, t]
        if t + 1 < t1 and pn != p:
            lg += CC[p, pn]
        g[t] = lg
    return g


class Evaluator:
    def __init__(self):
        self.E = SE.era_inputs()
        self.LX = {e: BM.logx(np.ascontiguousarray(self.E[e]['X'])) for e in ('spx', 'ndx')}
        self._s85 = None

    def era_dates(self, e):
        return self.E[e]['dates']

    def daily(self, e, dec):
        dec = np.ascontiguousarray(np.asarray(dec, np.int64)); assert len(dec) == len(self.E[e]['dates'])
        g = _g(self.LX[e], dec, BM.COSTC)
        return pd.DataFrame(dict(dec=dec, g=g, lg=g + np.log1p(self.E[e]['X'][2])), index=self.E[e]['dates'])

    def discovery(self, dec_spx, dec_ndx):
        a = self.daily('spx', dec_spx).loc['1955-01-03':'1985-12-31']
        b = self.daily('ndx', dec_ndx).loc['1986-01-02':'1999-12-31']
        ms = a['g'].groupby([a.index.year, a.index.month]).sum().values
        mn = b['g'].groupby([b.index.year, b.index.month]).sum().values
        D = np.r_[ms, mn].astype(np.float32); assert len(D) == 540
        return D, dict(adv_spx=float(a['g'].mean() * 252), adv_ndx=float(b['g'].mean() * 252), adv_all=float(np.r_[a['g'].values, b['g'].values].mean() * 252))

    def confirm(self, dec_ndx):
        if self._s85 is None: self._s85 = CF.s085_logret()
        x = self.daily('ndx', dec_ndx).loc['2000-01-03':'2014-12-31']
        s = self._s85['ndx'].reindex(x.index); ok = s.notna()
        return dict(adv_vs_1x=float(x['g'].mean() * 252), d_vs_s085=float((x['lg'][ok] - s[ok]).mean() * 252), ann_logret=float(x['lg'].mean() * 252))

    def ms1(self, dec_spx, dec_ndx, label=''):
        srv = MM.ms1._Server()
        ds = self.daily('spx', dec_spx); dn = self.daily('ndx', dec_ndx)
        dec = pd.concat([ds['dec'][ds.index < '1985-01-02'], dn['dec']])
        codes = sorted(set(np.unique(dec.values).tolist()) | {2})
        out = dict(label=label, real=MM.real_rows(srv, dec, codes))
        x = dn.loc['1986-01-02':'2014-12-31']; rr = np.expm1(x['lg'].values)
        if self._s85 is None: self._s85 = CF.s085_logret()
        s85 = self._s85['ndx'].loc['1986-01-02':'2014-12-31']
        P = MM.stream_paths(srv, x.index, rr); Q = MM.stream_paths(srv, s85.index, np.expm1(s85.values))
        conv = {}
        for bn in MM.ms1.BASES:
            if P[bn] is None or Q[bn] is None: conv[bn] = None; continue
            d = P[bn]['fc'] - Q[bn]['fc']
            conv[bn] = dict(rule_stream=float(np.median(P[bn]['fc'])), s085_stream=float(np.median(Q[bn]['fc'])), d_stream=float(np.median(d)))
        out['stream'] = conv; out['representative'] = 0.1616 + conv['dev250_path']['d_stream']
        return out
