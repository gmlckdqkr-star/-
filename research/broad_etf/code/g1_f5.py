"""BE1 F5: broad-ETF intermarket NDX timing signals through INFO GATE G1 (gate.py), trials=8. <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
import bdata as BD
D = BD.by_date(actual=True)
LV = np.exp(np.log1p(D).cumsum(skipna=True)).where(D.notna())
def R(n, k): return LV[n] / LV[n].shift(k) - 1
sec = list(BD.KF12)
sig = {}
sig['s1_stk_gt_bond63'] = R('VTI', 63) > R('TLT', 63)
sig['s2_cyc_gt_def63'] = (R('XLK', 63) + R('DUR', 63) + R('XLY', 63)) / 3 > (R('XLU', 63) + R('XLP', 63) + R('XLV', 63)) / 3
sig['s3_small_gt_mkt63'] = R('IWM', 63) > R('VTI', 63)
sig['s4_gold126_neg'] = (R('GLD', 126) < 0).where(R('GLD', 126).notna())
br = sum((LV[s] > LV[s].rolling(200).mean()).astype(float) for s in sec)
sig['s5_breadth7of11'] = br >= 7
sig['s6_banks_gt_mkt63'] = R('KBE', 63) > R('VTI', 63)
sig['s7_semis_gt_mkt63'] = R('SOXX', 63) > R('VTI', 63)
V = pd.DataFrame({k: v.astype(float).where(v.notna()) for k, v in sig.items()})
sig['s8_vote4of7'] = (V.sum(axis=1) >= 4)
out = {}
for k, s in sig.items():
    s = s.dropna()
    s = s[s.index >= pd.Timestamp('1954-01-01')]
    g = gate.test(s.astype(bool), trials=8, name=k, verbose=False)
    out[k] = g
    e = {era: (round(v['hit'], 4), round(v['hit_deflated'], 4), round(v['always_up'], 4)) if v else None for era, v in g.items() if era.startswith(('ndx', 'spx'))}
    print(k, g['verdict'], e)
json.dump(out, open('/mnt/project-files/research/broad_etf/results/g1_f5_le2014.json', 'w'), indent=1, default=str)
