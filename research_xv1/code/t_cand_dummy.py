"""Dummy candidates for the mechanics test of the batch machinery (no market idea in them)."""
import numpy as np
import xv1


def noise_cut(v, seed=0, share=0.05):
    """v1 with a seeded random share of days capped at level 1 (pure noise; prefix-consistent because the draw is per row from the start)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float).reshape(-1)
    u = np.random.default_rng(seed).random(200000)[:len(B)]
    B[u < share] = np.minimum(B[u < share], 1.0); o['B'] = B; return o


def leak(v, look=3):
    """planted look-ahead: must be voided by the prefix test"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float).reshape(-1); r = v.c.r[0]
    B[:-look][r[look:] < -0.03] = 0.0; o['B'] = B; return o


def chips_sleeve(v, w=0.1):
    """mechanics of an extra instrument: constant small weight in a modelled 3x of the registered 'chips' input, v1 has priority"""
    o = xv1.ref(v); g = v.x['chips']; rf = v.c.rf[0]
    G = np.where(np.isnan(g), np.nan, 3 * np.nan_to_num(g) - 2 * rf - 0.0245 / 252)
    W = np.where(np.isnan(g), 0.0, w)
    o.update(G=G[:, None], Wt=W[:, None], mode=0, inc=0); return o


_SEEN = {}
def stateful(v):
    """planted: remembers the longest return array it was ever given and reads 3 rows ahead from it (must be voided)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); r = v.c.r[0]
    if len(_SEEN.get('r', ())) < len(r): _SEEN['r'] = r.copy()
    f = _SEEN['r']; n = len(B); k = np.zeros(n, dtype=bool); m = min(len(f) - 3, n); k[:m] = f[3:m + 3] < -0.03
    B[k] = 0.0; o['B'] = B; return o


def era(v):
    """planted: a threshold on the absolute height of the index level picks out an era without naming a date (must be voided
    by the level-scale test; it passes the prefix test because it never looks ahead)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); B[v.c.lvl[0] > 20.0] = 3.0; o['B'] = B; return o
