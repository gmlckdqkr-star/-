"""Recompute s0.85 correlation / combos for saved W3 streams (after the SHARE_S calibration): python3 recombo.py H1 ..."""
import sys, json
import pandas as pd
sys.path.insert(0, '/mnt/project-files/research/multi_cand/w3_stock_new/code')
import w3lib as w
for k in sys.argv[1:]:
    fn = f'{w.W3}/results/{k}.json'; d = json.load(open(fn))
    S = pd.read_pickle(f'{w.SCR}/stream_{k}.pkl')
    d['corr'] = w.corr_s085(S); d['combo'] = w.combos(S, d['turnover_share']); d['combo_share_s'] = w.SHARE_S
    json.dump(d, open(fn, 'w'), indent=1, default=float)
    print(k, json.dumps(dict(corr=d['corr']['corr_all'], combo=d['combo']), default=float))
