"""H6 (lab DSL spec): the lab MS1 stream (stocks.ms1_stream) -> s0.85 correlation and combos; lab one-line numbers are
copied from the lab run (results/H6_lab_line.txt)."""
import sys, json, yaml
import pandas as pd
sys.path.insert(0, '/mnt/project-files/research/multi_cand/w3_stock_new/code')
import w3lib as w
from lab import stocks, dsl
spec = dsl.check_spec(yaml.safe_load(open(f'{w.W3}/specs/H6_mkt_resid_rev.yaml')))
m = stocks.ms1_stream(spec, w.panel())
S = pd.DataFrame(dict(r=m['ret'], q=m['basis_add']), index=pd.DatetimeIndex(m['dates']))
S.to_pickle(f'{w.SCR}/stream_H6.pkl')
res = dict(hypothesis='H6', stream_start=m['start'], turnover_share=m['turnover'], corr=w.corr_s085(S),
           combo=w.combos(S, m['turnover']), share_s=w.SHARE_S)
json.dump(res, open(f'{w.W3}/results/H6_stream.json', 'w'), indent=1, default=float)
print(json.dumps(res, default=float))
