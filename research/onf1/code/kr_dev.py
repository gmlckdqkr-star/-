"""Korean night leg inside the development window (2010-03-02..2014-12-31, data_cut only): the pre-registration promised this
split (KR leg reported separately for <=2014 and for the holdout).  Event-ordered engine code/eng.py, uploaded presets,
A = package assumptions (cash rf-2%p, no financing spread), S = project standard (cash 0, financing +0.4%p).
'tradable' = KR night sized with what is known at the 15:30 KST entry; 'look-ahead' = diagnostic kr_sync mode (not tradable).
In-sample for the presets (the upload tuned them on 1999-2026).   python -B code/kr_dev.py -> results/kr_dev_le2014.json"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import pandas as pd
from dataclasses import replace
import eng
rd = lambda p: pd.read_csv(p, index_col=0, parse_dates=True)
us, kr = rd(paths.CUT + 'us_le2014.csv'), rd(paths.CUT + 'kr_le2014.csv')
ASSUME = {'A': dict(cash_spread=0.02, fin_spread=0.0), 'S': dict(cash_spread=None, fin_spread=0.004)}
START, END = '2010-03-02', '2014-12-31'
def one(cfg, sync=False):
    A = eng.prepare(us, kr, cfg, start=START, end=END); eq, info = eng.run(A, cfg, kr_sync=sync); s = eng.stats(eq, info['fin'])
    return dict(cagr=s['cagr'], mdd=s['mdd'], first=str(eq.index[0].date()), last=str(eq.index[-1].date()))
res = {'window': [START, END], 'note': 'in-sample for the uploaded presets; <=2014 data only'}
for nm, cfg in (('v9', eng.V9), ('v10', eng.V10), ('PRESET_A', eng.PRESET_A)):
    for a, kw in ASSUME.items():
        u = one(replace(cfg, use_kr=False, **kw)); t = one(replace(cfg, **kw)); l = one(replace(cfg, **kw), sync=True)
        res['%s [%s]' % (nm, a)] = dict(us_only=u, us_kr_tradable=t, us_kr_lookahead=l)
        print('%-9s [%s] US-only %.1f%%/%.0f%% | US+KR tradable %.1f%%/%.0f%% | look-ahead(diagnostic) %.1f%%/%.0f%%  (%s..%s)' % (
            nm, a, u['cagr'] * 100, u['mdd'] * 100, t['cagr'] * 100, t['mdd'] * 100, l['cagr'] * 100, l['mdd'] * 100, t['first'], t['last']), flush=True)
json.dump(res, open(paths.RES + 'kr_dev_le2014.json', 'w'), indent=1)
