import os, sys, numpy as np, pandas as pd
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD
pan = DD.panel('REAL'); w = L.world('REAL'); idx = w['S'].index
print('REAL gaps', pan['meta']['gaps']); print('nanfrac', {k: v for k, v in pan['meta']['nanfrac'].items() if v > 0})
S = DD.src_series()
lo, hi = pd.Timestamp('1984-10-01'), pd.Timestamp('2014-12-31')
for k in ['DEF3', 'LTT', 'GOLD', 'VALUE', 'SPXsrc']:
    if k == 'SPXsrc': continue
    s = S[k]; s = s[(s.index >= lo) & (s.index <= hi)]
    off = s.index.difference(idx); cal = idx[(idx >= max(lo, s.index.min())) & (idx <= hi)]
    miss = cal.difference(s.index)
    print(k, 'n', len(s), 'dates not on calendar', len(off), 'sum of dropped r %.4f' % s.reindex(off).sum(), 'calendar days missing in series', len(miss), list(map(str, miss[:5])))
# annualised stats of the neutralised sleeves in REAL (t>=300)
for k in ['QQQ', 'SPX', 'DEF3', 'VALUE', 'GOLD', 'LTT', 'B10', 'TBILL', 'TQQQ', 'QLD']:
    a = pan[k][0][:, 300:]; inc = pan[k][1]
    print('%-6s mean %.4f vol %.4f' % (k, a.mean() * 252, a.std() * np.sqrt(252)))
