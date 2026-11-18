import os, sys, time, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std'); os.environ.setdefault('NUMBA_NUM_THREADS','2')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC, dfe
from dfctx import std
t0 = time.time(); END = pd.Timestamp('2014-12-31')
sys.path.insert(0, '/mnt/project-files/research/diversifier/code'); sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el, sl
print('modules', ii.__file__, el.__file__, sl.__file__)
el.CSPR = 10.0
jv = ii.SID.index('VALPROF4_L1'); jc = ii.SID.index('CAPE_L3')
def v2run(bn, w):
    S, SO = ii.arrays(bn); TQ, DEP, CU, IDL = ii._REFIN[bn]
    if w == (0, 0):
        Sa = np.zeros(S.shape[:2] + (1,), S.dtype); SOa = np.zeros_like(Sa); wa = np.zeros(1)
    else:
        v = S[:, :, jv].astype(np.float64) - 0.006 / 252; c = S[:, :, jc].astype(np.float64)
        Sa = np.ascontiguousarray(np.stack([v, c], 2).astype(S.dtype)); SOa = np.ascontiguousarray(np.stack([SO[:, :, jv], SO[:, :, jc]], 2)); wa = np.array(w, float)
    fin, E = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                      float(1 - wa.sum()), np.ascontiguousarray(wa), 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
    y = E.shape[1] / 252; cg = np.maximum(fin, 1e-9) ** (1 / y) - 1; md = (E / np.maximum.accumulate(E, 1) - 1).min(1)
    return cg, md, S
bn = 'dev250_path'
ii._REFIN[bn] = el.ref_inputs(el.ctx(bn, cspr=10.0))
v1, m1, S = v2run(bn, (0, 0)); v2, m2, S = v2run(bn, (.15, .10))
print('S shape', S.shape, 'SID', ii.SID)
capeA = S[:, :, jc].astype(np.float64).copy(); ii._ARR.clear()
Ssrc = sl.src(); dts = pd.DatetimeIndex(Ssrc['dates']); w_ = (dts >= pd.Timestamp('1986-01-03')) & (dts <= END)
EXV = float(np.mean(Ssrc['B10'][w_] - Ssrc['rf'][w_])); print('EXV %.6e' % EXV, 'keys', [k for k in Ssrc.keys()][:20])
B10orig = Ssrc['B10'].copy()
res = {}
for nm, shift in (('bx0', EXV), ('bx0_x2', 2*EXV)):
    Ssrc['B10'] = B10orig - shift
    vb, mb, Sb = v2run(bn, (.15, .10)); res[nm] = vb
    capeB = Sb[:, :, jc].astype(np.float64); ii._ARR.clear()
    dc = capeA - capeB
    print(nm, 'CAPE_L3 sleeve daily shift: median %.4e  share of days shifted %.3f  shifted days mean shift/EXV %.3f' % (np.median(dc[:, 300:]), np.mean(np.abs(dc[:, 300:]) > 1e-9), np.mean(dc[:, 300:][np.abs(dc[:, 300:]) > 1e-9]) / shift))
    vdiff = (S[:, :, jv].astype(np.float64) - Sb[:, :, jv].astype(np.float64)); print('   VALPROF4 changed days share %.4f' % np.mean(np.abs(vdiff) > 1e-12))
Ssrc['B10'] = B10orig
def rep(tag, a, b):
    d = a - b
    print('%-10s med(a) %.4f med(b) %.4f | diff of medians %+.3f pp | median paired diff %+.3f pp | share a>b %.3f' % (tag, np.median(a)*100, np.median(b)*100, 100*(np.median(a) - np.median(b)), 100*np.median(d), np.mean(d > 1e-5)))
rep('v2-v1', v2, v1); rep('v2bx0-v1', res['bx0'], v1); rep('v2bx0x2-v1', res['bx0_x2'], v1)
print('mdd p10 v1 %.4f v2 %.4f' % (np.percentile(m1, 10), np.percentile(m2, 10)))
np.savez('/tmp/vf_refute/v2paths.npz', v1=v1, v2=v2, bx0=res['bx0'])
print('done %.0fs' % (time.time() - t0))
