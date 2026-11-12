"""Dummy candidates for the mechanics test of the batch machinery (no market idea in them)."""
import numpy as np
import xv1


def noise_cut(v, seed=0, share=0.05):
    """v1 with a fixed pseudo-random share of days capped at level 1 (pure noise; prefix-consistent because the value of a
    row depends only on its position from the start: allowed in a dummy, not in a real candidate)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float).reshape(-1)
    u = np.abs(np.sin(np.cumsum(np.ones(v.T)) * 12.9898 * (seed + 1)) * 43758.5453) % 1.0
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


SEEN = {}
def stateful(v):
    """planted: remembers the longest return array it was ever given and reads 3 rows ahead from it (must be voided)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); r = v.c.r[0]
    if len(SEEN.get('r', ())) < len(r): SEEN['r'] = r.copy()
    f = SEEN['r']; n = len(B); k = np.zeros(n, dtype=bool); m = min(len(f) - 3, n); k[:m] = f[3:m + 3] < -0.03
    B[k] = 0.0; o['B'] = B; return o


def era(v):
    """planted: a threshold on the absolute height of the index level picks out an era without naming a date (must be voided
    by the level-scale test; it passes the prefix test because it never looks ahead)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); B[v.c.lvl[0] > 20.0] = 3.0; o['B'] = B; return o


def invent(v, w=0.1):
    """planted: an instrument return that is no registered input and no modelled fund (must be voided by the instrument check)"""
    o = xv1.ref(v); o.update(G=np.full((v.T, 1), 0.001), Wt=np.full((v.T, 1), w), mode=1, inc=0); return o


def own_brake(v):
    """planted: v1's brake with one parameter moved (must be voided by the output rules)"""
    o = xv1.ref(v); bp = np.array(o['bp'], dtype=float); bp[-1] += 1e-9; o['bp'] = bp; return o


def write_input(v):
    """planted: tries to change an input array in place (must be voided)"""
    o = xv1.ref(v); v.c.r[0][5] = 0.0; return o


def swap_input(v):
    """planted: replaces an input array of the view by another one (must be voided; v6: through a dict item, since the gate
    refuses any assignment to an attribute)"""
    o = xv1.ref(v); m = v.m; m['y10'] = m['y10'] * 1.0; return o


def crash(v):
    """planted: raises (must be voided, the batch goes on)"""
    return xv1.ref(v)['nothing']


def late(v, hundreds):
    """mechanics of T0: v1 until a fixed row of the view (100 * hundreds), then capped at level 1 on every fifth row"""
    row = 100 * hundreds
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); k = np.cumsum(np.ones(v.T)) - 1
    q = (k >= row) & (k % 5 == 0); B[q] = np.minimum(B[q], 1.0); o['B'] = B; return o
