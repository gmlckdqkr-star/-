"""Worlds for the self-tests and for the independent verification. No real market value after 2014-12-31 is used in them.

 old()        the calendar ends 2014-12-31 (real data, already seen by every lane)
 synth(seed)  the full calendar DATES with every market value after 2014-12-31 replaced before anything is computed: the
              index chain (return, cash rate, yields, spread, VIX) by a copy of old rows, the registered extra inputs by
              block-resampled old rows of the same series (noise where a series has fewer than 500 old rows). Periodic
              calendar fields stay as they are (they are dates, not market values). With extras=False no registered input
              can be read at all until the test supplies its own.
 scratch(dir) points the evaluator's output folder at a scratch folder (never a project folder).
Both worlds set xv1.WORLD: the evaluator then builds no real calendar after 2014-12-31 whatever else happens, and the
registered constants may be changed by a test. In the real world (WORLD None) they may not."""
import os, sys, zlib, shutil, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
from xv1 import jp, mkt


DEFAULT_OUT = '/tmp/xv1_world_out/'      # a test world never writes into the registered folder (xv1._writable refuses it too)


def _away():
    if os.path.realpath(xv1.OUT) == os.path.realpath(xv1.REG_OUT): os.makedirs(DEFAULT_OUT, exist_ok=True); xv1.OUT = DEFAULT_OUT


def old():
    xv1.WORLD = 'old'; xv1.CAL_END = xv1.A_END = xv1.OLD_END; _away()


def _none(names, idx):
    if names: raise PermissionError('synthetic world without extras: no registered input is readable')
    return {}


def synth(seed=0, extras=True):
    xv1.WORLD = 'synth'; _away()
    R, M = jp.calendar(xv1.CAL_START, xv1.CAL_END); X = jp.mkX(R, M, 'NDX')
    n0 = int(X.index.searchsorted(pd.Timestamp('2015-01-01'))); n1 = len(X) - n0; sh = 500 + 250 * int(seed)
    for c in ('r', 'rf', 'y10', 'y3m', 'cs', 'vix'): X.iloc[n0:, X.columns.get_loc(c)] = X[c].values[n0 - n1 - sh:n0 - sh]
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    xv1._FR.clear(); xv1._FR[xv1.CAL_END] = X; xv1._FR[xv1.A_END] = X.loc[:xv1.A_END]; xv1._REF.clear()
    real = _REAL.setdefault('extras', xv1.extras)
    if extras:
        def fake(names, idx):
            E = {k: np.array(a, dtype=np.float64) for k, a in real(names, idx).items()}
            m0 = int(idx.searchsorted(pd.Timestamp('2015-01-01'))); m1 = len(idx) - m0
            for k, a in E.items():
                if k.startswith('cal:') or m1 <= 0: continue
                g = np.random.default_rng([int(seed), zlib.crc32(k.encode())]); o = a[:m0]; ok = np.flatnonzero(~np.isnan(o))
                if len(ok) >= 500:
                    st = g.integers(ok[0], m0 - 20, m1 // 20 + 1); a[m0:] = o[(st[:, None] + np.arange(20)).ravel()[:m1]]
                else: a[m0:] = g.normal(0, 0.02, m1)
            return E
        xv1.extras = fake
    else: xv1.extras = _none
    return X


def scratch(tmp):
    """a fresh scratch output folder for a test; refuses anything that is not under /tmp or /home/claude"""
    if xv1.WORLD is None: raise PermissionError('declare a test world first')
    p = os.path.realpath(tmp)
    if not (p.startswith('/tmp/') or p.startswith('/home/claude/')) or 'project-files' in p: raise PermissionError('not a scratch folder: ' + p)
    shutil.rmtree(p, ignore_errors=True); os.makedirs(p); xv1.OUT = p + '/'
    return xv1.OUT


_REAL = {}
