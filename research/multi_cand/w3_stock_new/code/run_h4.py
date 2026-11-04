"""H4: s0.85 with its cash days filled by the lab example stk_lowvol_top50 stock stream (lab stocks.ms1_stream:
conservative book after cost and dividend tax, before 22%). Same mix engine as the combos (w3lib.filler)."""
import sys, json, yaml
import pandas as pd
sys.path.insert(0, '/mnt/project-files/research/multi_cand/w3_stock_new/code')
import w3lib as w
from lab import stocks, dsl
spec = yaml.safe_load(open('/mnt/project-files/research/lab/specs/examples/stk_lowvol_top50.yaml'))
P = w.panel()
m = stocks.ms1_stream(dsl.check_spec(spec), P)
S = pd.DataFrame(dict(r=m['ret'], q=m['basis_add']), index=pd.DatetimeIndex(m['dates']))
S.to_pickle(f'{w.SCR}/stream_lowvol50.pkl')
res = dict(hypothesis='H4', book='lab example stk_lowvol_top50 (score -vol(252), invvol(63), top 50, quarterly)',
           stream_start=m['start'], turnover_share=m['turnover'], corr_lowvol50=w.corr_s085(S),
           filler=w.filler(S), combo_lowvol50_reference=w.combos(S, m['turnover']), share_s=w.SHARE_S)
json.dump(res, open(f'{w.W3}/results/H4.json', 'w'), indent=1, default=float)
print(json.dumps(res, default=float, indent=1))
