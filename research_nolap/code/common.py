"""NL1 shared helpers. <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import jp, iv, ov, bk, rx
RES = '/mnt/project-files/research/nolap/results'
FOMC = '/mnt/project-files/research/nolap/results/fomc_events.json'

def ctx_dates():
    """per context: DatetimeIndex of path days (P,T) as numpy datetime64 matrix"""
    C = std.contexts(); out = {}
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); out['real_ndx_86_14'] = X.index.values[C['real_ndx_86_14'].ii]
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
    out['dev250_glued'] = X.index.values[C['dev250_glued'].ii]; out['dev250_path'] = X.index.values[C['dev250_path'].ii]
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX')
    for nm in ('real_spx_55_85', 'real_spx_70_85'): out[nm] = X.index.values[C[nm].ii]
    return C, out

def fomc_days(start='1994-02-04', end='2014-12-31'):
    ev = [e for e in json.load(open(FOMC)) if e['kind'] == 'Meeting']
    ds = sorted(pd.Timestamp(e['date']) for e in ev)
    keep = []
    for i, d in enumerate(ds):   # two 'Meeting' entries within 3 days -> keep the later one
        if i + 1 < len(ds) and (ds[i + 1] - d).days <= 3: continue
        keep.append(d)
    return [d for d in keep if pd.Timestamp(start) <= d <= pd.Timestamp(end)]

def shift_left(F, k):
    """B[:, p] = F[:, p+k] (decision k days before the return day), zero-padded"""
    B = np.zeros_like(F); B[:, :-k] = F[:, k:]; return B

def s085_daily(c):
    """daily after-tax equity ratio stream of s0.85 on a context (P, T-WARM)"""
    B, bfn, bp, fs = std.s085(c); fin, EE = std.engine(c, B, bfn, bp, fs); return fin, EE
