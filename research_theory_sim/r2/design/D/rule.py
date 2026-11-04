"""FCCL rule (lane TS2 round 2, designer D): a constant index exposure E0, executed with drift tracking.
Under the FCCL theory's own prior no timing signal (realised volatility, capital ledger, term-spread carry) survived costs:
the premium rises with risk when intermediary capital is scarce, so cutting exposure in high volatility loses, and the carry
signal is too weak. What remains is the growth-optimal constant exposure of the prior (about 1.25). Because the 3x/cash mix
drifts while the held level is unchanged, the rule replicates the engine's position and changes level only when that brings
the effective exposure clearly closer to E0 (penalty THETA). Causal, scale-invariant, pure numpy.
"""
import math
import numpy as np

INPUTS = ('close', 'rf')
PARAMS = {'E0': 1.25, 'THETA': 0.35}

_WARM = 300         # engine warm-up columns (not traded)
_DELAY = 2          # engine delay (decision at close t trades at close t+2)
_ACT_HL = 20.0      # half-life (days) of the "market is trading" indicator
_LEVELS = np.arange(0.0, 3.0001, 0.5)


def target_levels(close, rf, y10=None, params=PARAMS):
    E0 = float(params['E0']); theta = float(params['THETA'])
    c = np.array(close, dtype=np.float64, copy=True)
    if c.ndim == 1:
        c = c[None, :]
    P, T = c.shape
    prev = np.empty_like(c); prev[:, 0] = np.nan; prev[:, 1:] = c[:, :-1]
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    r = np.zeros_like(c)
    r[ok] = c[ok] / prev[ok] - 1.0                                # scale-invariant simple return
    f = np.array(rf, dtype=np.float64, copy=True).reshape(P, T)
    f = np.where(np.isfinite(f), f, 0.0)
    act = (ok & (r != 0.0)).astype(np.float64)
    g3 = 1.0 + 3.0 * r - 2.0 * f - 0.0245 / 252.0                 # 3x product daily growth (engine definition)
    gc = 1.0 + np.maximum(f - 0.02 / 252.0, 0.0) * (1.0 - 0.154)  # cash daily growth (engine definition)
    lam_a = 0.5 ** (1.0 / _ACT_HL)
    ea = np.zeros(P)
    held = np.zeros(P); u = np.zeros(P); cur = np.zeros(P)
    q = np.zeros((P, _DELAY))
    B = np.zeros((P, T))
    rows = np.arange(P)
    for t in range(T):
        ea = lam_a * ea + (1.0 - lam_a) * act[:, t]
        D = np.where(ea > 0.5, min(max(E0, 0.0), 3.0), 0.0)      # market not trading yet / long flat stretch -> cash
        # replica of the engine's executed position (the 3x/cash mix drifts while the level is unchanged)
        if t >= _WARM:
            want = q[:, 0].copy(); q[:, :-1] = q[:, 1:]
            if t > _WARM:
                a = u * g3[:, t]; b = (1.0 - u) * gc[:, t]
                tot = a + b
                u = np.where(tot > 0, a / np.where(tot > 0, tot, 1.0), 0.0)
            m = (want != cur) | (t == _WARM)
            u = np.where(m, want / 3.0, u); cur = np.where(m, want, cur)
            pend = q[:, -1] != cur
            Ek = np.where(pend, q[:, -1], 3.0 * u)                # effective exposure if the held level is kept
            pen = theta
        else:
            Ek = held
            pen = 0.0
        keep = np.abs(Ek - D)
        dist = np.abs(_LEVELS[None, :] - D[:, None]) + pen
        valid = (np.abs(_LEVELS[None, :] - held[:, None]) >= 0.5) | ((_LEVELS[None, :] == 0.0) & (held[:, None] > 0.0))
        dist = np.where(valid, dist, np.inf)
        j = np.argmin(dist, axis=1)
        ch = dist[rows, j] < keep
        held = np.where(ch, _LEVELS[j], held)
        B[:, t] = held
        if t == _WARM - 1:
            q[:, :] = held[:, None]
        elif t >= _WARM:
            q[:, -1] = held
    return B
