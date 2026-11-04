"""M3 environment: reuse the verified ETX1 engine (research/etf_ext/code/etxeng.py) with caches redirected to this scratchpad.
<=2014 only (every source is cut at 2014-12-31 by the loaders)."""
import os, sys
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, '/mnt/project-files/research/etf_ext/code')
import etxdata as XD
import bdata as BD
XD.CACHE = SCR + 'cache/'; BD.CACHE = SCR + 'cache/'
import etxeng as G
G.CACHE = SCR + 'cache/'
