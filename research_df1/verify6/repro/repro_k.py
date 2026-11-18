"""Verifier k_s check: monthly 1928-01..1985-12, DEF3 (KF NoDur/Hlth/Utils daily EW) vs KF market (Mkt-RF + RF). Rows after 1985-12-31 dropped at load."""
import sys, zipfile, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/df6v/repro'); import mysim as M
CUT = pd.Timestamp('1985-12-31')
z = zipfile.ZipFile('/mnt/project-files/research/broad_etf/data/raw/kf/F-F_Research_Data_Factors_daily_CSV.zip')
nm = [n for n in z.namelist() if n.lower().endswith('.csv')][0]; rows = []
for ln in z.read(nm).decode('latin1').splitlines():
    p = [x.strip() for x in ln.split(',')]
    if len(p) >= 5 and p[0].isdigit() and len(p[0]) == 8 and int(p[0]) <= 19851231:
        rows.append((pd.Timestamp(p[0]), (float(p[1]) + float(p[4])) / 100, float(p[4]) / 100))
mk = pd.DataFrame(rows, columns=['d', 'mkt', 'rf']).set_index('d')
d3 = M.def3_series(CUT); rf = M.load_csv('RF', CUT)
mon = lambda s: (1 + s[s.index >= '1928-01-01']).groupby([s[s.index >= '1928-01-01'].index.year, s[s.index >= '1928-01-01'].index.month]).prod() - 1
df = pd.DataFrame({'D3': mon(d3), 'MKT': mon(mk['mkt']), 'RF': mon(rf)}).dropna()
ex = df[['D3', 'MKT']].sub(df['RF'], axis=0)
sh = lambda x: x.mean() / x.std(ddof=1)
y = ex.index.get_level_values(0)
for tag, s in (('all', slice(None)), ('28_55', y <= 1955), ('56_85', y >= 1956)):
    e = ex[s]; print(tag, len(e), 'k=%.4f' % (sh(e['D3']) / sh(e['MKT'])), 'SR_def3=%.3f SR_mkt=%.3f (ann)' % (sh(e['D3']) * 12 ** .5, sh(e['MKT']) * 12 ** .5))
