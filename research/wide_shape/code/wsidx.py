"""WS1 A1: index direction oracle map (long 3x / inverse 3x / cash) on MS1 contexts. <=2014 only.
MS1 conditions: cost 0.3%/side, 22% yearly tax on net realized gains (deduction 0.25 x start, no carry-forward),
final liquidation tax, 3x = 3r-2rf-2.45%/252, cash = (rf-2%/252)*(1-0.154).
Inverse 3x (conservative): -3r + rf - 2.45%/252 - 3*dy/252 (dy NDX 1.5%, SPX 5% flat).
Oracle: blocks of h days from WARM; per block, with prob p the better of the allowed products, else the other one
(two-state shapes) . Blocks are independent draws."""
import numpy as np
from numba import njit

WARM = 300
COST = 0.003
TAX = 0.22
DED = 0.25


@njit(cache=True)
def run_paths(prod, h, p, seed, mode):
    """prod: [P, 3, T] daily returns of products (0 = L3, 1 = I3, 2 = cash) already from WARM on.
    mode 0: states {L3, I3}; mode 1: states {L3, cash}.
    returns final CAGR per path (after tax incl. liquidation)."""
    P = prod.shape[0]; T = prod.shape[2]
    out = np.empty(P)
    np.random.seed(seed)
    for i in range(P):
        val = 1.0; basis = 1.0; held = -1; real_y = 0.0
        nb = (T + h - 1) // h
        for b in range(nb):
            s = b * h; e = min(T, s + h)
            # block product returns
            g0 = 1.0; g1 = 1.0; g2 = 1.0
            for t in range(s, e):
                g0 *= 1 + prod[i, 0, t]; g1 *= 1 + prod[i, 1, t]; g2 *= 1 + prod[i, 2, t]
            if mode == 0:
                best = 0 if g0 >= g1 else 1
                other = 1 - best
            else:
                best = 0 if g0 >= g2 else 2
                other = 2 if best == 0 else 0
            st = best if np.random.random() < p else other
            if st != held:
                if held >= 0:
                    # sell: cost and realize
                    proceeds = val * (1 - COST)
                    real_y += proceeds - basis
                    val = proceeds
                val = val * (1 - COST)   # buy cost
                basis = val
                held = st
            # daily walk with yearly tax on day multiples of 252
            for t in range(s, e):
                val *= 1 + prod[i, st, t]
                if (t + 1) % 252 == 0:
                    tx = TAX * max(0.0, real_y - DED)
                    if tx > 0:
                        frac = tx / val
                        if frac > 0.999: frac = 0.999
                        val *= (1 - frac); basis *= (1 - frac)
                    real_y = 0.0
        # final liquidation
        proceeds = val * (1 - COST)
        real_y += proceeds - basis
        tx = TAX * max(0.0, real_y - DED)
        fin = proceeds - tx
        if fin < 1e-9: fin = 1e-9
        out[i] = fin ** (252.0 / T) - 1
    return out


def products(r, rf, dy):
    """r, rf [P, T] (already sliced from WARM) -> [P, 3, T]"""
    L3 = 3 * r - 2 * rf - 0.0245 / 252
    I3 = -3 * r + rf - 0.0245 / 252 - 3 * dy / 252
    C = (rf - 0.02 / 252) * (1 - 0.154)
    return np.ascontiguousarray(np.stack([L3, I3, C], axis=1))


def hold3(r, rf):
    """same-basis TQQQ-type hold, for parity with MS1 hold3x (engine differs slightly)."""
    L3 = 3 * r - 2 * rf - 0.0245 / 252
    E = np.cumprod(1 + L3, axis=1)
    fin = E[:, -1] * (1 - COST) * (1 - COST)
    fin = fin - TAX * np.maximum(fin - 1, 0)
    return np.maximum(fin, 1e-9) ** (252.0 / r.shape[1]) - 1
