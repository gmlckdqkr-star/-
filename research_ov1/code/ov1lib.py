"""OV1 helper (2026-11-05). <=2014 only. Wraps the locked MS1 standard (research/measure_std/std.py) so a lane can
(1) overlay a NEW external daily/weekly/monthly series on v1 (= s0.85 = C3sig + av23s brake .85), and
(2) report every MS1 basis with the series handled two ways:
    'glued'  : external value of the ORIGINAL calendar date of each resampled day (upper bound, like dev250_glued)
    'path'   : the external series re-built ALONG each resampled path by cumulating its own day-to-day changes
               (same treatment std.path_flags gives y10/y3m/cs) -> HEADLINE for MS1. Transform must be computed on it.
Run with the MS1 interpreter:  ~/.cache/lab/ms1-venv/bin/python  (system python3 has a broken pandas).
API
  D = dates()                       -> {basis: DatetimeIndex of that context's X}
  C = std.contexts()                -> {basis: Ctx}  (Ctx.ii = (P,T) row indices into that basis' X)
  g = gather(series, basis)         -> (P,T) array, glued values (ffill onto trading dates, NaN before series start)
  p = path_series(series, basis)    -> (P,T) array, path-rebuilt level (start value + cumsum of diffs on the path)
  B = v1_B(c)                       -> (P,T) v1 daily target level 0/1/3 at close t (2-day delay is applied by engine)
  T = measure2(name, make2)         -> like std.measure but make2(c, basis) gets the basis name. Returns rows per basis
        make2 must return (B, bfn, bp, fstep[, engine_kw]); use v1_parts(c) for v1's brake: (bfn, bp, fstep)
  T['HEADLINE_MS1'] = dev250_path cagr ; compare with ref 0.1616 (path) and 0.3108 (real_ndx_86_14)
Notes: SPX 1955-85 contexts usually have no external data -> gather() gives NaN -> make2 must fall back to v1 there
       (report those rows as 'not covered'). Never read rows after 2014-12-31.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, jp, ov, bk, rx, iv  # noqa

_D = {}
def dates():
    if _D: return _D
    R, M = jp.calendar('1984-01-03', '2014-12-31'); _D['real_ndx_86_14'] = jp.mkX(R, M, 'NDX').index
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); ix = jp.mkX(R, M, 'NDX').index
    _D['dev250_glued'] = ix; _D['dev250_path'] = ix
    R, M = jp.calendar('1928-01-03', '1985-12-31'); ix = jp.mkX(R, M, 'SPX').index
    _D['real_spx_55_85'] = ix; _D['real_spx_70_85'] = ix
    return _D

def _onto(series, basis):
    s = pd.Series(series).sort_index(); s = s[s.index <= pd.Timestamp('2014-12-31')]
    return s.reindex(dates()[basis].union(s.index)).ffill().reindex(dates()[basis]).values.astype(float)

def gather(series, basis):
    c = std.contexts()[basis]; v = _onto(series, basis); return v[c.ii]

def path_series(series, basis):
    c = std.contexts()[basis]; v = _onto(series, basis)
    if basis != 'dev250_path': return v[c.ii]
    d = np.r_[np.nan, np.diff(v)]; out = np.empty(c.ii.shape)
    for i in range(c.ii.shape[0]):
        pos = c.ii[i]; dd = d[pos].copy(); dd[0] = 0.0; dd = np.where(np.isnan(dd), 0.0, dd)
        out[i] = v[pos[0]] + np.cumsum(dd)
        if np.isnan(v[pos[0]]):   # series not started at path start: NaN until first real value on the path
            vv = v[pos]; k = np.argmax(~np.isnan(vv)) if (~np.isnan(vv)).any() else len(vv)
            out[i, :k] = np.nan; out[i, k:] = vv[k] + np.cumsum(np.r_[0.0, dd[k + 1:]])
        out[i][np.isnan(v[pos])] = np.nan   # days whose source date has no data stay NaN (no info -> lane falls back to v1)
    return out

def v1_B(c): return bk.C3sig(c)
def v1_parts(c): _, bfn, bp, fs = std.s085(c); return bfn, bp, fs

def measure2(name, make2, verbose=True):
    out = {}
    for bn, c in std.contexts().items():
        m = make2(c, bn); kw = m[4] if len(m) > 4 else {}
        cand, fc = std.row(*std.engine(c, m[0], m[1], m[2], m[3], **kw))
        rB, rbf, rbp, rfs = std.s085(c); ref, fr = std.row(*std.engine(c, rB, rbf, rbp, rfs))
        q, _ = std.row(*std.hold(c, 1)); d = fc - fr
        cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=ref['cagr'], hold1x=q['cagr'])
        out[bn] = cand
        if verbose: print('%-16s %-15s ' % (name, bn) + ' '.join('%s=%.4f' % kv for kv in cand.items()), flush=True)
    out['HEADLINE_MS1'] = out['dev250_path']['cagr']; out['REAL_NDX'] = out['real_ndx_86_14']['cagr']
    out['BEATS_V1_BOTH'] = bool(out['dev250_path']['cagr'] > 0.1616 and out['real_ndx_86_14']['cagr'] > 0.3108)
    return out

if __name__ == '__main__':   # self-check: v1 through measure2 must reproduce 0.1616 / 0.3108
    T = measure2('v1_selfcheck', lambda c, bn: (v1_B(c),) + v1_parts(c))
    print('HEADLINE', T['HEADLINE_MS1'], 'REAL', T['REAL_NDX'])
