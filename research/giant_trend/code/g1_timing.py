"""G1 (gate.py) on the market-timing giants: signal True = fully in equities at that month end."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/giant_trend/code')
from gtsetup import *
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
res = {}
for n in ('TUD_B', 'MAR_T', 'GRA_C', 'DRU_T', 'ONE_T'):
    dec = STRATS[n][0](); cur = None; vals = []
    for t in range(c.T):
        d = dec[t]
        if d is not None and d[0] == 'w': cur = d[1].get('CASH', 0.0) < 1e-9 and sum(d[1].values()) > 0
        vals.append(np.nan if cur is None else float(cur))
    idx = pd.DatetimeIndex([p.to_timestamp(how='end').normalize() for p in c.idx])
    sig = pd.Series(vals, index=idx).dropna()
    r = gate.test(sig, trials=25, name=n, verbose=False)
    res[n] = {k: ({kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} if isinstance(v, dict) else v) for k, v in r.items()}
    print(n, r['verdict'], {k: (round(v['hit'], 3), round(v['hit_deflated'], 3), round(v['always_up'], 3)) for k, v in r.items() if isinstance(v, dict)})
json.dump(res, open('/mnt/project-files/research/giant_trend/results/g1_timing.json', 'w'), indent=1)
