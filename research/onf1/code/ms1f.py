"""MS1-conform measurement of US futures night/day strategies (same pools, same path indices, same path-recomputed
macro flags as research/measure_std/std.py; engine = code/eng.py US-only).  <=2014 data only.

MS1 conditions kept: dev pool 1986-2014 NDX price index (no dividends), 250-day blocks, 500 paths x 30y, flags recomputed
on the path, signal delay 2 trading days, yearly tax + final liquidation tax, paired comparison with s0.85 (v1) on the
same paths.  Futures-specific: cost per side c_us (default 0.83bp), derivatives tax 11%, cash in the futures account
earns 0 (project rule A47), futures excess return = price return - (rf + s), s = 0.4%/yr financing spread as in MF1
(dividend yield ignored, same as the v1 measurement on the price index).

Night/day split of each source day:
  date >= 1999-03-10 : real QQQ split (price based), day = NDX log return - QQQ night log return
  date <  1999-03-10 : synthetic  night = alpha + beta*cc + eps  (beta, residual shape estimated on QQQ 1999-03..2014-12)
     mode 'C' : alpha = 0 before 1999-03-10                     (no night premium where it cannot be observed)
     mode 'M' : alpha = dev-estimated intercept from 1993-01-29 (first SPY ETF print; SPY shows a night premium
                1993-98 with real opening prints), alpha = 0 before 1993-01-29   (evidence-based central case)
     mode 'H' : alpha = dev-estimated intercept everywhere before 1999-03-10   (upper bound)
     mode 'Z' : synthetic alpha = 0 on EVERY date (also 1999-2014)  -> value of the structure without any night premium
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
sys.path.insert(0, paths.PROJ + '/research/measure_std')
import numpy as np, pandas as pd
from numba import njit, prange
import std, jp, ov, iv
import eng

W_ID = 6.5 / (24 * 1.45); W_ON = 1 - W_ID        # share of a trading day's rf accrual: day vs night (avg 1.45 calendar days)
CUT = pd.Timestamp('1999-03-10'); CUT_M = pd.Timestamp('1993-01-29')
_B = {}


def _qqq_split(file=None):
    file = file or paths.CUT + 'us_le2014.csv'
    us = pd.read_csv(file, index_col=0, parse_dates=True)
    q = us.dropna(subset=['qqq_open', 'qqq_close']).copy()
    on = np.log(q.qqq_open / q.qqq_close.shift()); cc_ndx = np.log(us.ndx / us.ndx.shift()).reindex(q.index)
    d = pd.DataFrame({'on': on, 'cc': cc_ndx}).dropna()
    return d


def _model():
    d = _qqq_split()
    sig = d.cc.rolling(20).std().shift(1)
    x = d.dropna(); s = sig.reindex(x.index)
    m = s.notna(); x = x[m]; s = s[m]
    beta = np.cov(x.on, x.cc)[0, 1] / x.cc.var(); alpha = x.on.mean() - beta * x.cc.mean()
    z = (x.on - alpha - beta * x.cc) / s
    return float(alpha), float(beta), z.values, d


def bases():
    """name -> dict(dates, r (source daily simple returns), rf, ii, F_alarm (P,T) bool, ctx)"""
    if _B: return _B
    C = std.contexts()
    def src(a, b, s):
        R, M = jp.calendar(a, b); X = jp.mkX(R, M, s); return X
    Xn = src('1984-01-03', '2014-12-31', 'NDX'); a, b, P, blk, seed = iv.POOLS['dev250']; Xd = src(a, b, 'NDX'); Xs = src('1928-01-03', '1985-12-31', 'SPX')
    for nm, X in (('real_ndx_86_14', Xn), ('dev250_glued', Xd), ('dev250_path', Xd), ('real_spx_55_85', Xs), ('real_spx_70_85', Xs)):
        c = C[nm]
        _B[nm] = dict(dates=X.index, src_r=X['r'].values, ii=c.ii, r=c.r, rf=c.rf, alarm=(c.F['inv'] | c.F['shock6m']), ctx=c)
    return _B


def split_source(dates, src_r, mode, seed=11, real_file=None, demean=False, cut_m=None):
    """per source row: (night log return, day log return).  real_file: take the real QQQ nights from this file (holdout
    windows only); the synthetic model (alpha, beta, residuals) is always estimated on the <=2014 cut.
    demean=True (measurement correction after the phase-2 audit): the drawn residual has its mean over the synthetic rows
    (from 1986-01-02) removed, so 'alpha = 0' really is zero drift whatever the seed."""
    alpha, beta, z, d = _model()
    if real_file: d = _qqq_split(real_file)
    cc = np.log1p(src_r)
    s = pd.Series(cc, index=dates); sig = s.rolling(20, min_periods=5).std().shift(1).bfill().values
    g = np.random.default_rng(seed); zz = z[g.integers(0, len(z), len(cc))]
    eps = zz * sig
    if demean:
        syn = np.ones(len(cc), bool) if mode == 'Z' else np.asarray(dates < CUT)
        pre = syn & np.asarray(dates >= pd.Timestamp('1986-01-02'))
        if not pre.any(): pre = syn
        eps = eps - np.where(syn, eps[pre].mean(), 0.0)
    syn0 = beta * cc + eps                              # alpha = 0
    on = syn0.copy()
    if mode == 'H': on = on + alpha
    if mode == 'M': on = on + alpha * (dates >= (pd.Timestamp(cut_m) if cut_m else CUT_M))
    if mode != 'Z':
        real = d.on.reindex(dates).values; m = (dates >= CUT) & np.isfinite(real)
        on[m] = real[m]
    return on, cc - on


@njit(cache=True, parallel=True)
def _paths(r, on_l, id_l, rf, sig, ma_ok_below, ma_ok_above, alarm, warm, delay,
           dc, dmax, nc, nmax, step, use_shock, shock, shock_cap, use_crisis,
           c_us, tax, k, fl, bmin, closs, cmult, cdays, fs, cint, ded, bdel):
    P, T = r.shape
    fin = np.empty(P); mdd = np.empty(P); w7 = np.empty(P); w12 = np.empty(P)
    for p in prange(P):
        Ln = np.zeros(T); Ld = np.zeros(T); s = False; bh = np.ones(T)
        for t in range(T):
            if ma_ok_below[p, t] and alarm[p, t]: s = True
            elif ma_ok_above[p, t] or not alarm[p, t]: s = False
            sg = sig[p, t]
            if not (sg > 0.0): continue
            d = min(dmax, dc / (sg * sg)); n = min(nmax, nc / (sg * sg))
            d = math.floor(d / step + 1e-9) * step; n = math.floor(n / step + 1e-9) * step
            if use_shock and shock[p, t]:
                d = min(d, shock_cap); n = min(n, shock_cap)
            if use_crisis and s: d = 0.0; n = 0.0
            Ld[t] = d; Ln[t] = n
        E = 1.0; peak = 1.0; snap = 1.0; cd = 0; N = 0.0; Ld_s = 0.0; b_s = 1.0; pnl = 0.0; pk = 1.0; dd = 0.0
        for t in range(warm, T):
            if (t - warm) % 252 == 0 and t > warm:
                tx = tax * max(pnl - ded, 0.0); E -= tx; snap -= tx; peak -= tx; pnl = 0.0
            f_on = math.exp(on_l[p, t]) - 1.0 - (rf[p, t] + fs / 252) * 0.8132
            f_id = math.exp(id_l[p, t]) - 1.0 - (rf[p, t] + fs / 252) * 0.1868
            if cint > 0: E += E * max(rf[p, t] - 0.02 / 252, 0.0) * (1 - 0.154)     # optimistic: cash earns rf-2%p (after 15.4%)
            x = N * f_on; E += x; pnl += x
            cur = N * (1.0 + f_on); tgt = Ld_s * b_s * E
            if tgt > cur: tgt = cur
            if tgt < 0.0: tgt = 0.0
            c = abs(cur - tgt) * c_us; E -= c; pnl -= c
            x = tgt * f_id; E += x; pnl += x
            if E < 1e-9: E = 1e-9
            if cd > 0: cd -= 1
            if E / snap - 1.0 < -closs: cd = cdays
            if E > peak: peak = E
            snap = E
            b = k * (E / peak - fl) / (1.0 - fl)
            if b > 1.0: b = 1.0
            if b < bmin: b = bmin
            if cd > 0: b *= cmult
            bh[t] = b
            if bdel > 0: b = bh[t - bdel] if t - bdel >= warm else 1.0     # brake/cool-down through the same delay as v1
            cur = tgt * (1.0 + f_id); j = t - delay
            tn = Ln[j] * b * E
            c = abs(cur - tn) * c_us; E -= c; pnl -= c
            N = tn; Ld_s = Ld[j]; b_s = b
            if E > pk: pk = E
            if E / pk - 1.0 < dd: dd = E / pk - 1.0
            if t - warm == 7 * 252 - 1: w7[p] = E
            if t - warm == 12 * 252 - 1: w12[p] = E
        E -= tax * max(pnl - ded, 0.0)
        yrs = (T - warm) / 252.0
        fin[p] = max(E, 1e-9) ** (1.0 / yrs) - 1.0; mdd[p] = dd
    return fin, mdd, w7, w12


SPLIT = dict(seed=11, demean=False, cut_m=None, carry=False)
# pre-registered runs: seed 11, no de-meaning.  run_fix.py: 30 seeds, demean=True.
# Sensitivities outside the registration (run_sens.py only): cut_m = start date of the mode-M premium (default 1993-01-29),
# carry=True = 'carry-neutral' synthetic night: + rf*(W_ON - beta) on synthetic rows (night earns its financing cost plus the
# beta share of the index excess return; the day leg loses the same amount, close-to-close unchanged).


def _skey(basis, mode): return ('split', basis, mode, SPLIT['seed'], SPLIT['demean'], SPLIT['cut_m'], SPLIT['carry'])


def split_on_path(basis, mode):
    """(night log return, day log return) on the path grid of the basis, with the SPLIT options applied."""
    B = bases()[basis]; ii = B['ii']; key = _skey(basis, mode)
    if key not in B:
        on, idl = split_source(B['dates'], B['src_r'], mode, SPLIT['seed'], B.get('real_file'), SPLIT['demean'], SPLIT['cut_m'])
        on, idl = on[ii], idl[ii]
        if SPLIT['carry']:
            syn = np.ones(len(B['dates']), bool) if mode == 'Z' else np.asarray(B['dates'] < CUT)
            adj = np.where(syn[ii], B['ctx'].rf * (W_ON - _model()[1]), 0.0); on = on + adj; idl = idl - adj
        for k in [k for k in B if isinstance(k, tuple) and k[0] == 'split']: del B[k]     # keep one split per basis (62 MB each on dev250)
        B[key] = (np.ascontiguousarray(on), np.ascontiguousarray(idl))
    return B[key]


def measure_one(cfg: eng.Cfg, basis, mode='C', delay=2, s=0.004, cint=0, ded=0.0, bdel=0):
    B = bases()[basis]
    on_l, id_l = split_on_path(basis, mode)
    c = B['ctx']; r = B['r']
    lr = np.log1p(r); n = cfg.vol_win
    c1 = np.cumsum(np.c_[np.zeros(len(r)), lr], axis=1); c2 = np.cumsum(np.c_[np.zeros(len(r)), lr * lr], axis=1)
    m = (c1[:, n:] - c1[:, :-n]) / n; v = ((c2[:, n:] - c2[:, :-n]) / n - m * m) * n / (n - 1)
    sig = np.c_[np.full((len(r), n - 1), np.nan), np.sqrt(np.maximum(v, 0) * 252)]
    ma = c.sma(cfg.ma_win); lvl = c.lvl
    below = lvl < ma * (1 - cfg.band); above = lvl > ma * (1 + cfg.band)
    shock = c.F['shock6m']
    fin, mdd, w7, w12 = _paths(r, np.ascontiguousarray(on_l), np.ascontiguousarray(id_l), np.ascontiguousarray(B['rf']), sig,
                               below, above, np.ascontiguousarray(B['alarm']), ov.WARM, delay,
                               cfg.us_day_c, cfg.us_day_max, cfg.us_night_c, cfg.us_night_max, cfg.step,
                               cfg.use_shock_cap, np.ascontiguousarray(shock), cfg.shock_cap, cfg.use_crisis,
                               cfg.c_us, cfg.tax, cfg.brake_k, cfg.brake_floor, cfg.brake_min, cfg.cool_loss, cfg.cool_mult, cfg.cool_days, s, cint, ded, bdel)
    return fin, mdd, w7, w12


_REF = {}
def ref_s085(basis):
    if basis not in _REF:
        c = bases()[basis]['ctx']; rB, rbf, rbp, rfs = std.s085(c); fr, EE = std.engine(c, rB, rbf, rbp, rfs); _REF[basis] = fr
    return _REF[basis]


def measure(name, cfg, mode='C', delay=2, verbose=True, s=0.004, cint=0, ded=0.0, bdel=0, bases_=('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')):
    out = {}
    for bn in bases_:
        fin, mdd, w7, w12 = measure_one(cfg, bn, mode, delay, s, cint, ded, bdel); fr = ref_s085(bn); d = fin - fr
        row = dict(cagr=float(np.median(fin)), mdd=float(np.median(mdd)), w7=float(np.median(w7)), w12=float(np.median(w12)),
                   d_vs_v1=float(np.median(d)), pw_vs_v1=float(np.mean(d > 1e-5)), ref_v1=float(np.median(fr)))
        if len(fin) > 1: row.update(p10=float(np.percentile(fin, 10)), dd80=float(np.mean(mdd <= -0.8)), dd95=float(np.mean(mdd <= -0.95)))
        out[bn] = row
        if verbose: print('%-22s %-15s mode %s d%d ' % (name, bn, mode, delay) + ' '.join('%s=%.3f' % kv for kv in row.items()), flush=True)
    return out


if __name__ == '__main__':
    from dataclasses import replace
    a, b, z, d = _model(); print('dev split model 1999-03..2014: alpha/day %.5f (%.1f%%/yr) beta %.3f resid z std %.3f n %d' % (a, a * 252 * 100, b, z.std(), len(z)))
    US = dict(use_kr=False, cash_spread=None)
    cands = {'v9-US': replace(eng.V9, **US), 'v10-US': replace(eng.V10, **US), 'A-US': replace(eng.PRESET_A, **US),
             'v9-US nocool': replace(eng.V9, cool_loss=9.9, **US), 'v9-US nocool nobrake': replace(eng.V9, cool_loss=9.9, brake_k=1e9, **US)}
    for nm, cfg in cands.items():
        for mode in ('C', 'Z', 'H'):
            measure(nm, cfg, mode, 2, bases_=('dev250_path', 'real_ndx_86_14') if mode != 'C' else ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'))
