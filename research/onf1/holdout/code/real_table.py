"""Tradable-timing real-history table for the uploaded presets (information; these presets were tuned on 1999-2026).
A = package assumptions (cash rf-2%p, no financing spread);  S = project standard (cash 0, financing +0.4%p).
POST-2014 NUMBERS: lives in holdout/code/, writes holdout/real_table_presets.csv.
  python -B holdout/code/real_table.py > holdout/real_table.log"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'code'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import json
import numpy as np, pandas as pd
from dataclasses import replace
from eng import *
us, kr = load(); usx, _ = load(ext=True)
rows = []
def one(tag, cfg, start, end=None, ext=False, sync=False):
    A = prepare(usx if ext else us, kr, cfg, start=start, end=end); eq, info = run(A, cfg, kr_sync=sync); s = stats(eq, info['fin'])
    rows.append(dict(tag=tag, start=start, end=str(eq.index[-1].date()), cagr=s['cagr'], mdd=s['mdd'], sharpe=s['sharpe'], worst_day=s['worst_day']))
    return eq, s
ASSUME = {'A': dict(cash_spread=0.02, fin_spread=0.0), 'S': dict(cash_spread=None, fin_spread=0.004)}
for nm, cfg in (('v9', V9), ('v10', V10), ('PRESET_A', PRESET_A)):
    for a, kw in ASSUME.items():
        for st in ('1999-03-10', '2010-03-02', '2015-01-02', '2020-01-02'):
            e1, s1 = one('%s US-only [%s] ->10-07' % (nm, a), replace(cfg, use_kr=False, **kw), st)
            e2, s2 = one('%s US-only [%s] ->11-09' % (nm, a), replace(cfg, use_kr=False, **kw), st, ext=True)
            if st != '1999-03-10':
                e3, s3 = one('%s US+KR tradable [%s] ->10-08' % (nm, a), replace(cfg, **kw), st)
                e4, s4 = one('%s US+KR look-ahead(diagnostic) [%s] ->10-08' % (nm, a), replace(cfg, **kw), st, sync=True)
                print('%-9s [%s] %s | US-only %.1f%%/%.0f%%  (->11-09 %.1f%%/%.0f%%) | US+KR tradable %.1f%%/%.0f%% | look-ahead %.1f%%/%.0f%%' % (
                    nm, a, st, s1['cagr'] * 100, s1['mdd'] * 100, s2['cagr'] * 100, s2['mdd'] * 100, s3['cagr'] * 100, s3['mdd'] * 100, s4['cagr'] * 100, s4['mdd'] * 100), flush=True)
            else:
                e3, s3 = one('%s US+KR(2010-03~) tradable [%s] ->10-08' % (nm, a), replace(cfg, **kw), st)
                print('%-9s [%s] %s | US-only %.1f%%/%.0f%%  (->11-09 %.1f%%/%.0f%%) | US+KR(2010~) tradable %.1f%%/%.0f%%' % (
                    nm, a, st, s1['cagr'] * 100, s1['mdd'] * 100, s2['cagr'] * 100, s2['mdd'] * 100, s3['cagr'] * 100, s3['mdd'] * 100), flush=True)
        if a == 'S':
            eqA = prepare(usx, kr, replace(cfg, use_kr=False, **kw), start='1999-03-10'); e, info = run(eqA, replace(cfg, use_kr=False, **kw))
            print('   %s US-only [S] change 2026-10-07 -> 2026-11-05: %.1f%% ; -> 11-09: %.1f%% ; drawdown from peak at 11-05: %.1f%%' % (
                nm, (e['2026-11-05'] / e['2026-10-07'] - 1) * 100, (e.iloc[-1] / e['2026-10-07'] - 1) * 100, (e['2026-11-05'] / e[:'2026-11-05'].max() - 1) * 100))
            y = yearly(e); print('   yearly:', ' '.join('%d:%+.0f' % (k, v * 100) for k, v in y.items()))
pd.DataFrame(rows).to_csv(paths.HOLD + 'real_table_presets.csv', index=False, float_format='%.5f')
