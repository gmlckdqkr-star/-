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
