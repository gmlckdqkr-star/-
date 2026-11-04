"""FCCL rule (lane TS2 round 2, designer D): carry-tilted constant exposure, executed with drift tracking.
Desired index exposure = E0 + TILT * (smoothed term spread - 1%), the funding-carry channel of the theory (a steep curve
refills intermediary capital, so the equity drift is higher); vol timing and ledger tilts are left out because they lost
on the theory's own synthetic worlds. Because the 3x/cash mix drifts while the held level is unchanged, the rule tracks
the effective exposure of its own position (engine rules replicated) and changes level only when that brings the
exposure clearly closer to the desired one (penalty THETA). Causal, scale-invariant, pure numpy.
"""
import math
import numpy as np

INPUTS = ('close', 'rf', 'y10')
PARAMS = {'E0': 1.25, 'TILT': 0.18, 'HSM': 120, 'THETA': 0.35}

_S0 = 0.01          # normal term spread (prior centre of the normal carry), fixed
_SCLIP = 0.03       # spread deviation clip (+-3 pp)
_WARM = 300         # engine warm-up columns (not traded)
_DELAY = 2          # engine delay (decision at close t trades at close t+2)
_LEVELS = np.arange(0.0, 3.0001, 0.5)


def _clean(close, rf, y10):
    c = np.array(close, dtype=np.float64, copy=True)
    if c.ndim == 1:
        c = c[None, :]
    P, T = c.shape
    prev = np.empty_like(c); prev[:, 0] = np.nan; prev[:, 1:] = c[:, :-1]
    ok = np.isfinite(c) & np.isfinite(prev) & (c > 0) & (prev > 0)
    r = np.zeros_like(c)
    r[ok] = c[ok] / prev[ok] - 1.0
    f = np.array(rf, dtype=np.float64, copy=True).reshape(P, T)
    f = np.where(np.isfinite(f), f, 0.0)
    if y10 is None:
        y = np.full((P, T), np.nan)
    else:
        y = np.array(y10, dtype=np.float64, copy=True).reshape(P, T)
    act = (ok & (r != 0.0)).astype(np.float64)
    return r, f, y, act


def target_levels(close, rf, y10=None, params=PARAMS):
    E0 = float(params['E0']); tilt = float(params['TILT']); hsm = float(params['HSM']); theta = float(params['THETA'])
    r, f, y, act = _clean(close, rf, y10)
    P, T = r.shape
    lam_s = 0.5 ** (1.0 / hsm); lam_a = 0.5 ** (1.0 / 20.0)
    g3 = 1.0 + 3.0 * r - 2.0 * f - 0.0245 / 252.0                 # 3x product daily growth (engine definition)
    gc = 1.0 + np.maximum(f - 0.02 / 252.0, 0.0) * (1.0 - 0.154)  # cash daily growth (engine definition)
    sm = np.full(P, _S0); ea = np.zeros(P)
    held = np.zeros(P); u = np.zeros(P); cur = np.zeros(P)
    q = np.zeros((P, _DELAY))
    B = np.zeros((P, T))
    rows = np.arange(P)
    for t in range(T):
        # desired exposure (data <= t only)
        ea = lam_a * ea + (1.0 - lam_a) * act[:, t]
        S = y[:, t] / 100.0 - 252.0 * f[:, t]
        fin = np.isfinite(S)
        sm = np.where(fin, lam_s * sm + (1.0 - lam_s) * np.where(fin, S, 0.0), sm)
        dev = np.clip(sm - _S0, -_SCLIP, _SCLIP)
        D = E0 + tilt * 100.0 * np.where(fin, dev, 0.0)
        D = np.clip(D, 0.0, 3.0)
        D = np.where(ea > 0.5, D, 0.0)                            # market not trading yet / flat stretch -> cash
        # replica of the engine's executed position (mix of 3x product and cash drifts while the level is unchanged)
        if t >= _WARM:
            want = q[:, 0].copy(); q[:, :-1] = q[:, 1:]
            if t > _WARM:
                a = u * g3[:, t]; b = (1.0 - u) * gc[:, t]
                tot = a + b
                u = np.where(tot > 0, a / np.where(tot > 0, tot, 1.0), 0.0)
            m = (want != cur) | (t == _WARM)
            u = np.where(m, want / 3.0, u); cur = np.where(m, want, cur)
            pend = q[:, -1] != cur
            Ek = np.where(pend, q[:, -1], 3.0 * u)                # exposure if the held level is kept
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
