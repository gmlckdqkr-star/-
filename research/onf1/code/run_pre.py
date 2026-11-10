"""Run the 12 pre-registered ONF1 candidates on the MS1 bases (<=2014).  python -B code/run_pre.py [T|F|P] """
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np
from dataclasses import replace
import ntilt, ms1f, eng
which = sys.argv[1] if len(sys.argv) > 1 else 'TFP'
OUT = paths.RES
T = {'T1': dict(impl=0, tau=1.0, gate=0, phi=0.15), 'T2': dict(impl=0, tau=0.5, gate=0, phi=0.075), 'T3': dict(impl=0, tau=2.0, gate=0, phi=0.30),
     'T4': dict(impl=0, tau=1.0, gate=1, phi=0.15), 'T5': dict(impl=0, tau=1.0, gate=2, phi=0.15), 'T6': dict(impl=0, tau=1.0, gate=0, vc=0.09, phi=0.15)}
F = {'F1': dict(impl=1, tau=1.0, gate=0), 'F2': dict(impl=1, tau=2.0, gate=0), 'F3': dict(impl=1, tau=1.0, gate=1)}
res = {}
def go(group, tag):
    for nm, kw in group.items():
        for mode in ('C', 'M', 'H', 'Z'):
            bs = ntilt.BASES if mode in ('C', 'M') else ('dev250_path', 'real_ndx_86_14')
            res['%s|%s|base' % (nm, mode)] = ntilt.measure(nm, mode, bases_=bs, **kw)
        res['%s|C|fee2' % nm] = ntilt.measure(nm + ' fee x2', 'C', bases_=('dev250_path', 'real_ndx_86_14'), fee=0.000166, **kw)
    json.dump(res, open(OUT + 'pre_%s_le2014.json' % tag, 'w'), indent=1)
if 'T' in which: go(T, 'T')
if 'F' in which: res.clear(); go(F, 'F')
if 'P' in which:
    res.clear(); US = dict(use_kr=False, cash_spread=None)
    for nm, cfg in (('P1 v9-US', replace(eng.V9, **US)), ('P2 v10-US', replace(eng.V10, **US)), ('P3 A-US', replace(eng.PRESET_A, **US))):
        for mode in ('C', 'M', 'H', 'Z'):
            bs = ntilt.BASES if mode in ('C', 'M') else ('dev250_path', 'real_ndx_86_14')
            res['%s|%s|base' % (nm, mode)] = ms1f.measure(nm, cfg, mode, 2, bases_=bs)
        res['%s|C|fee2' % nm] = ms1f.measure(nm + ' fee x2', replace(cfg, c_us=0.000166), 'C', 2, bases_=('dev250_path', 'real_ndx_86_14'))
    json.dump(res, open(OUT + 'pre_P_le2014.json', 'w'), indent=1)
