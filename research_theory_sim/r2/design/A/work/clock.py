import numpy as np
from rulelib import logret

def clock_rule(close, p0=0.015, th_c=1.4, d_r=0.15, L_c=0.0, L_r=3.0, hl_f=5, hl_m=25, hl_tr=20, hl_dd=None,
               kelly=True, Lb_const=1.0, d_exit=None, prior_vol=0.17, prior_years=5.0, Lb_cap=3.0, ret_state=False, th_r=1.0, use_trend=True, base_vol='long', rf=None, kp_years=None, dd_need=None):
    lr = logret(close)
    P, T = lr.shape
    af = 1 - np.exp(np.log(0.5) / hl_f); am = 1 - np.exp(np.log(0.5) / hl_m); at = 1 - np.exp(np.log(0.5) / hl_tr)
    v0 = (prior_vol ** 2) / 252
    vf = np.full(P, v0); vm = np.full(P, v0)
    sq = np.zeros(P); n = 0.0; k = prior_years * 252
    lp = np.zeros(P); ema = np.zeros(P); hi = np.zeros(P)
    state = np.zeros(P, dtype=np.int8)   # 0 normal, 1 cascade, 2 recovery
    B = np.empty((P, T)); st = np.empty((P, T), dtype=np.int8) if ret_state else None
    de = d_r * 0.5 if d_exit is None else d_exit
    sx = np.zeros(P); lrf = np.log1p(rf) if rf is not None else None
    for t in range(T):
        x = lr[:, t]
        if lrf is not None: sx = sx + x - lrf[:, t]
        lp = lp + x
        vf = (1 - af) * vf + af * x * x
        vm = (1 - am) * vm + am * x * x
        ema = (1 - at) * ema + at * lp
        hi = np.maximum(hi, lp)
        sq = sq + x * x; n += 1
        vL = (sq + k * v0) / (n + k)          # long-run variance, shrunk to prior
        dd = lp - hi
        casc = (vf > th_c * th_c * vm) & ((lp < ema) if use_trend else True)
        if dd_need is not None: casc = casc & (dd < -dd_need)
        past_peak = vf < th_r * th_r * vm
        s0 = state
        new = s0.copy()
        new = np.where((s0 == 0) & casc, 1, new)
        new = np.where((s0 == 1) & past_peak & (dd < -d_r), 2, new)
        new = np.where((s0 == 1) & past_peak & (dd >= -d_r), 0, new)
        new = np.where((s0 == 2) & casc, 1, new)
        new = np.where((s0 == 2) & ~casc & (dd > -de), 0, new)
        state = new
        if kelly:
            vb = vL if base_vol == 'long' else vm
            if kp_years is None: pe = p0
            else:
                kp = kp_years * 252; pe = (sx + kp * p0 / 252) / (n + kp) * 252
            Lb = np.clip(pe / (vb * 252) + 0.5, 0.0, Lb_cap)
        else:
            Lb = np.full(P, Lb_const)
        L = np.where(state == 0, Lb, np.where(state == 1, L_c, np.maximum(L_r, Lb)))
        B[:, t] = L
        if ret_state: st[:, t] = state
    return (B, st) if ret_state else B
