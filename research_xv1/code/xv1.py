"""XV1 sealed block evaluator (see PREREG_XV1_STRUCTURE.md).

One continuous real-NDX account from 1986-01-02 to CAL_END on the locked MS1 chain (std / beng.run1), scored by
3-year calendar block. Numbers are produced for DESIGN and WEAK blocks only. The two SEALED blocks (2016-18,
2022-24) are masked to NaN before any statistic is computed and are never returned, printed or stored.

A candidate is  make(ctx) -> (B, bfn, bp, fstep[, engine_kw])  exactly as in research/measure_std/std.py.
Candidate code receives the full context (the account is continuous) and must be pure: no printing, plotting or
writing of any series."""
import os, sys, json, time, hashlib
import numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_xv1')   # own cache: the shared one collides with other sessions
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import jp, ov, bk, beng, rx

CAL_START, ACC_START, CAL_END, OLD_END = '1984-01-03', '1986-01-02', '2026-08-31', '2014-12-31'
Y0, BLEN, EMB = 1986, 3, 63
SEALED = (10, 12)                      # 2016-18, 2022-24
ZERO_CASH = dict(cspr=10.0)            # idle cash earns nothing (owner rule 2026-11-11)
OUT = '/mnt/project-files/research/xv1/'


def kind_of(b):
    """'D' design, 'W' weak validation (<= 2014, already seen), 'S' sealed."""
    if b % 2 == 1: return 'D'
    return 'S' if b in SEALED else 'W'


def years_of(b): return '%d-%02d' % (Y0 + BLEN * b, (Y0 + BLEN * b + BLEN - 1) % 100)


def build(end=CAL_END):
    """context of the real path (P = 1) and the dates of the account days k = 0.."""
    R, M = jp.calendar(CAL_START, end); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp(ACC_START)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :])
    c.idx = X.index[i0:]                 # all T rows (warm-up + account days), for candidate data alignment
    return c, X.index[i0 + ov.WARM:]


class Cal:
    """block calendar of the account days"""
    def __init__(s, dates):
        s.dates = dates; s.n = len(dates)
        s.blk = ((dates.year - Y0) // BLEN).astype(int)
        s.kind = np.array([kind_of(b) for b in s.blk])
        first = np.r_[True, s.blk[1:] != s.blk[:-1]]
        start = np.maximum.accumulate(np.where(first, np.arange(s.n), 0))
        s.rank = np.arange(s.n) - start              # 0-based trading-day number inside the block
        s.scored = s.rank >= EMB                     # first EMB days of every block are not scored
        s.sealed = s.kind == 'S'
        s.blocks = sorted(set(s.blk.tolist()))

    def mask(s, kinds, since=None):
        m = s.scored & np.isin(s.kind, list(kinds))
        if since is not None: m = m & (s.dates >= pd.Timestamp(since))
        return m


def account(c, make, **kw):
    """one continuous run. returns rec (days, 4): equity after costs and yearly tax, level in force, brake target, base."""
    m = make(c); k = dict(ZERO_CASH); k.update(m[4] if len(m) > 4 else {}); k.update(kw); k['fstep'] = m[3]
    _, rec = beng.run_path(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]),
                           np.ascontiguousarray(m[0][0], dtype=np.float64), np.ascontiguousarray(bk.features(c)[0]),
                           m[1], np.asarray(m[2], dtype=np.float64), **k)
    return rec


def xlog(E, cal):
    """daily log growth; sealed days are set to NaN here, before anything else looks at the series."""
    x = np.full(len(E), np.nan); x[1:] = np.log(E[1:] / E[:-1])
    x[cal.sealed] = np.nan
    return x


def hold3(c): return (np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5)


def hold1_x(c, cal):
    r = c.r[0, ov.WARM:] - 0.002 / 252
    x = np.log1p(r); x[0] = np.nan; x[cal.sealed] = np.nan
    return x


def ann(x, m):
    n = int(m.sum())
    return float(252.0 * np.nansum(x[m]) / n) if n else float('nan')


def table(x, cal, kinds=('D', 'W'), ref=None):
    """per-block annualised log growth for the allowed kinds only"""
    rows = []
    for b in cal.blocks:
        kd = kind_of(b)
        if kd not in kinds or kd == 'S': continue
        m = cal.scored & (cal.blk == b)
        if not m.any(): continue
        row = dict(block=b, years=years_of(b), kind=kd, n=int(m.sum()), ann=ann(x, m))
        if ref is not None: row['ref'] = ann(ref, m); row['d'] = row['ann'] - row['ref']
        rows.append(row)
    return rows


def boot_p(d, block=EMB, draws=10000, seed=20261111):
    """one-sided circular block bootstrap p-value for mean(d) > 0 (centred)."""
    d = np.asarray(d, float); n = len(d); g = np.random.default_rng(seed)
    nb = int(np.ceil(n / block)); st = g.integers(0, n, (draws, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(draws, -1)[:, :n] % n
    m = d[idx].mean(axis=1) - d.mean()
    return float(np.mean(m >= d.mean()))


def sets(x, cal, ref=None):
    out = {}
    for nm, kinds, since in (('design', 'D', None), ('weak', 'W', None), ('design_post2014', 'D', '2015-01-01')):
        m = cal.mask(kinds, since); o = dict(n=int(m.sum()), ann=ann(x, m))
        if ref is not None: o['ref'] = ann(ref, m); o['d'] = o['ann'] - o['ref']
        out[nm] = o
    return out


def ledger(entry):
    os.makedirs(OUT, exist_ok=True)
    entry = dict(entry); entry['ts'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    with open(OUT + 'LEDGER.jsonl', 'a') as f: f.write(json.dumps(entry, ensure_ascii=False) + '\n')
