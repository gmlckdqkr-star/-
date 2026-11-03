"""Example plugin (a shape the DSL cannot express directly): trend QLD with a re-entry wait that grows with each
exit inside a year. Contract: func(F, sleeves, params) -> DataFrame of weights, index = F.index, columns in sleeves
(+ CASH). F holds only the spec's `inputs` (read like price(x)); no file / panel access. Row t may use rows <= t only
(the lab truncation test checks this on the dev data and on bar paths)."""
import numpy as np
import pandas as pd


def weights(F, sleeves, params):
    n = int(params.get('n', 200)); base = int(params.get('wait', 5)); w = float(params.get('w', 0.88))
    px = F['QQQ'].values
    sma = pd.Series(px).rolling(n, min_periods=n).mean().values
    up = px > sma
    out = np.zeros(len(px)); on = False; wait_until = -1; exits = []
    for t in range(len(px)):
        if on and not up[t]:
            on = False
            exits = [e for e in exits if t - e < 252] + [t]
            wait_until = t + base * len(exits)
        elif not on and up[t] and t >= wait_until:
            on = True
        out[t] = w if on else 0.0
    return pd.DataFrame({sleeves[0]: out}, index=F.index)
