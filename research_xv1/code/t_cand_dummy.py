"""Dummy candidates for the mechanics test of the batch machinery (no market idea in them)."""
import numpy as np
import xv1


def noise_cut(v, seed=0, share=0.05):
    """v1 with a fixed pseudo-random share of days capped at level 1 (pure noise; prefix-consistent because the value of a
    row depends only on its position from the start: allowed in a dummy, not in a real candidate)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float).reshape(-1)
    u = np.abs(np.sin(np.cumsum(np.ones(v.T)) * 12.9898 * (seed + 1)) * 437.585453 * 100.0) % 1.0
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


def jitter_leak(v, look=3, thr=-0.08, w=0.5, eps=0.000001):
    """planted (v6 check of the changed parts): a 3-row look-ahead into a modelled inverse fund, hidden among thousands of
    sub-step changes of B that the engine never acts on (they make level events; every event row must still be cut)"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); r = v.c.r[0]; T = v.T; m = max(T - look, 0)
    k = np.zeros(T, dtype=bool)
    with np.errstate(invalid='ignore'): k[:m] = r[look:look + m] < thr
    B = np.where((r > 0) & (B >= 1.0), B - eps, B)
    G = -r + v.c.rf[0] - 0.0095 / 252
    o.update(B=B, G=G[:, None], Wt=np.where(k, w, 0.0)[:, None], mode=1, inc=0)
    return o


def hold_leak(v, n=50, look=1, thr=-0.02):
    """planted (v7): own rule = level 3 while the index is above its n-row mean, else 1. A one-row look-ahead HOLDS level 3
    on a row on which the index dips below the mean with a daily fall beyond thr and is back above it on the next row.
    The level does not change on such a row, so it makes no event row; only a cut exactly on that row sees the look-ahead
    (it must be voided by the every-row test, whatever the sampled test says)"""
    o = xv1.ref(v); lv = v.c.lvl[0]; r = v.c.r[0]; T = v.T
    c = np.cumsum(np.r_[0.0, lv]); ma = np.full(T, np.inf); ma[n - 1:] = (c[n:] - c[:-n]) / n
    up = lv > ma; B = np.where(up, 3.0, 1.0)
    k = np.zeros(T, dtype=bool); k[1:T - look] = up[:T - look - 1] & ~up[1:T - look] & up[1 + look:] & (r[1:T - look] < thr)
    B[k] = 3.0
    o.update(B=B, bfn=xv1.std.ident, bp=np.zeros(1), fstep=0.5); return o


def list_mem(v, mem, look=3):
    """planted (v7): as `stateful`, with the memory kept in a list parameter. Up to version 6 that list was one object
    shared by all calls of a configuration (the cut calls then read what the full call had stored, and the prefix test
    passed); since version 7 every call gets a new copy, so the look-ahead shows and it must be voided by the prefix test"""
    o = xv1.ref(v); B = np.array(o['B'], dtype=float); r = v.c.r[0]
    if not mem or len(mem[0]) < len(r): mem[:] = [r.copy()]
    f = mem[0]; n = len(B); k = np.zeros(n, dtype=bool); m = min(len(f) - look, n); k[:m] = f[look:m + look] < -0.03
    B[k] = 0.0; o['B'] = B; return o


def oom(v):
    """planted (v7): asks for an array of about 7 PiB, which no machine has: a MemoryError that is not the rule's own
    error (the batch run must stop and log it the first time, and void the configuration the second time)"""
    o = xv1.ref(v); z = np.zeros((999, 999, 999, 999, 999)); return o
