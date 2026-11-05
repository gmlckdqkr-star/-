import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
D = '/mnt/project-files/research/nx1/data/'
lab = gate.labels(); days = lab['spx_55_85'].index.append(lab['ndx_86_14'].index).sort_values()
cal = pd.bdate_range('1950-01-01', '2014-12-31')
def monthly_to_daily(m):          # value of obs month m usable from first business day of m+2
    m = m.dropna(); idx = [(d + pd.offsets.MonthBegin(2)) for d in m.index]
    s = pd.Series(m.values, index=pd.DatetimeIndex(idx)); s = s[s.index <= '2014-12-31']
    return s.reindex(cal, method='ffill')
res = {}
for ser in ('IPG3344S', 'IPG334S'):
    x = pd.read_csv(D + ser + '.csv', index_col=0, parse_dates=True).iloc[:, 0]
    x = x[x.index <= '2014-10-01']
    yoy = x.rolling(3).mean().pct_change(12)
    acc = yoy - yoy.shift(6)
    for tag, m in (('yoy', yoy > 0), ('acc', acc > 0)):
        mm = m.where(yoy.notna() if tag == 'yoy' else acc.notna())
        s = monthly_to_daily(mm.astype(float)).dropna().astype(bool)
        g = gate.test(s, trials=4, name=f'{ser}_{tag}', verbose=False)
        res[f'{ser}_{tag}'] = g
        print(ser, tag, {k: (round(v['hit'], 3), round(v['always_up'], 3), round(v['hit_deflated'], 3), v['n']) for k, v in g.items() if isinstance(v, dict)}, g['verdict'], 'on-share', round(s.mean(), 2))
json.dump(res, open('/mnt/project-files/research/nx1/results/k2.json', 'w'), indent=1, default=float)
