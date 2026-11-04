# what does the master's 'representative conversion' (16.2 + d_stream) give for strategies whose path value is known?
import os, sys, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/numba_cache'
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/m1/code'); sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import ms1
import m1_ms1 as MM, m1_confirm as CF, m1_engine as EN, m1_search as SE
srv = ms1._Server()
E = SE.era_inputs(); e = E['ndx']
sel = (e['dates'] >= '1986-01-02') & (e['dates'] <= '2014-12-31')
dts = e['dates'][sel]
s85 = CF.s085_logret()['ndx'].loc['1986-01-02':'2014-12-31']
Q = MM.stream_paths(srv, s85.index, np.expm1(s85.values))
out = {}
for nm, code in (('hold 1x NDX', 2), ('hold 3x NDX', 0)):
    ret = e['X'][code][sel]
    P = MM.stream_paths(srv, dts, ret)
    for bn in ('dev250_path', 'real_ndx_86_14'):
        d = P[bn]['fc'] - Q[bn]['fc']
        print('%-12s %-15s own stream median %.4f | s0.85 stream %.4f | d_stream %.4f | 16.2+d = %.4f' % (
            nm, bn, np.median(P[bn]['fc']), np.median(Q[bn]['fc']), np.median(d), 0.1616 + np.median(d)), flush=True)
