"""Make the <=2014 cut used by the design-readable code:  holdout/data/{us,kr}.csv -> data_cut/{us,kr}_le2014.csv.
Rows after 2014-12-31 are dropped.  The back-adjusted price columns (*_adj) are dropped as well, because their LEVELS are
rescaled by dividends/splits paid after 2014 (the return columns r_cc/r_on/r_id/f_on/f_id are ratios and unaffected).
  python -B holdout/code/cut_data.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'code'))
import paths
import pandas as pd
os.makedirs(paths.CUT, exist_ok=True)
for nm in ('us', 'kr'):
    d = pd.read_csv(paths.DATA + nm + '.csv', index_col=0, parse_dates=True).loc[:'2014-12-31']
    d = d.drop(columns=[c for c in d.columns if c.endswith('_adj')])
    d.to_csv(paths.CUT + nm + '_le2014.csv.tmp'); os.replace(paths.CUT + nm + '_le2014.csv.tmp', paths.CUT + nm + '_le2014.csv'); print(nm, d.index[0].date(), d.index[-1].date(), d.shape, list(d.columns))
