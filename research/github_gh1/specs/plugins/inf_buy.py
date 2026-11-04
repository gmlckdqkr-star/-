"""GH1 B: 'infinite buying' (라오어 무한매수법-style) on TQQQ: n splits, buy 1 part when close <= avg cost,
1/2 part when avg < close <= avg*(1+tp), sell all at close >= avg*(1+tp); on exhaustion sell 1/4 (quarter stop) unless
stop=0. Own simplified re-implementation of the public rule description. Output = own-book TQQQ weight."""
import numpy as np
import pandas as pd


def weights(F, sleeves, params):
    p = F['level(TQQQ)'].values.astype(float)
    n = float(params.get('n', 40)); tp = float(params.get('tp', 0.10)); stop = int(params.get('stop', 1))
    C = 1.0; S = 0.0; cost = 0.0; k = 0.0; u = C / n
    out = np.zeros(len(p))
    for t in range(len(p)):
        px = p[t]
        if not np.isfinite(px) or px <= 0:
            out[t] = 0.0; continue
        avg = cost / S if S > 0 else 0.0
        if S > 0 and px >= avg * (1 + tp):
            C += S * px; S = 0.0; cost = 0.0; k = 0.0; u = C / n
        else:
            if S <= 0 or px <= avg:
                q = 1.0
            elif px <= avg * (1 + tp):
                q = 0.5
            else:
                q = 0.0
            q = min(q, n - k)
            spend = min(q * u, C)
            if spend > 1e-12:
                S += spend / px; cost += spend; C -= spend; k += q
            if k >= n - 1e-9 and stop:
                sell = S * 0.25
                C += sell * px; cost *= 0.75; S -= sell; k = k * 0.75
                u = (C + 0.0) / max(n - k, 1.0)
        eq = S * px + C
        out[t] = (S * px / eq) if eq > 0 else 0.0
    return pd.DataFrame({sleeves[0]: out}, index=F.index)
