"""Dump one world's raw arrays (<=2014 only; code cuts at load) to npz for my own simulator.
Uses df5lib.world (bootstrap index + market arrays) and df5data.panel (per-asset net daily returns) only."""
import os, sys, json, time, numpy as np
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/repro/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5lib as L, df5data as DD
MAN = json.load(open('/mnt/project-files/research/df5/data/MANIFEST.json'))['assets']
DD.set_files({k: '/mnt/project-files/research/df5/data/clean/%s.csv' % k for k in MAN if k in DD.SLEEVES or k in ('STAP', 'UTIL', 'HLTH')})
DD.eligibility()
wn = sys.argv[1]; t0 = time.time()
w = L.world(wn); m = w['m']
print('world', wn, m['r'].shape, 'ov.WARM', L.W, 'load %.0fs' % (time.time() - t0), flush=True)
# source calendar end check without printing any date beyond 2014
print('src max <= 2014-12-31:', bool(w['S'].index.max() <= L.END))
pan = DD.panel(wn)
out = dict(r=np.asarray(m['r'], float), rf=np.asarray(m['rf'], float), ii=np.asarray(w['ii']))
out['month'] = w['S'].index.month.values[w['ii']].astype(np.int8)
for k in ['QQQ', 'QLD', 'TQQQ', 'TBILL', 'B10', 'LTT', 'GOLD', 'DEF3', 'SPX', 'VALUE', 'TMF']:
    a, inc, hv = pan[k]
    out['RET_' + k] = np.asarray(a, float)
    out['INC_' + k] = np.asarray(inc, float) if isinstance(inc, np.ndarray) else np.array(float(inc))
    out['HV_' + k] = np.array(hv)
out['spx_raw'] = np.nan_to_num(w['S']['SPX'].values.astype(float)[w['ii']])
print('shifts/yr', {k: round(v * 252, 5) for k, v in pan['meta']['shift'].items() if k in ('B10', 'LTT', 'GOLD', 'DEF3', 'VALUE')})
np.savez('/tmp/df5v/repro/data/%s.npz' % wn, **out)
print('saved %.0fs' % (time.time() - t0))
