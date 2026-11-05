"""AW data: v1 reference inputs + candidate sleeve streams per MS1 basis (<=2014). Product drags as in v002 CMB3."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/diversifier/code'); sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
sys.path.insert(0, '/mnt/project-files/research/adaptive_w/code')
import ii, el, dv2, aw
BASES = ['real_spx_55_85', 'real_spx_70_85', 'real_ndx_86_14', 'dev250_path']
DRAG = {'VALPROF4_L1': 0.006, 'SMALL_L3': 0.05}          # VALPROF4 version drag (v002) ; TNA vs synthetic 3x small (CMB3)
_C = {}
def load(bn, names):
    key = (bn, tuple(names))
    if key in _C: return _C[key]
    S, SO = ii.arrays(bn); A = []; B = []
    for nm in names:
        if nm in ii.SID: j = ii.SID.index(nm); x = S[:, :, j].astype(np.float64); so = SO[:, :, j]
        else:
            S2, SO2 = dv2.arrays(bn); j = dv2.NM.index(nm); x = S2[:, :, j].astype(np.float64); so = SO2[:, :, j]
        x = x - DRAG.get(nm, 0.0) / 252; A.append(x); B.append(so)
    out = (np.ascontiguousarray(np.stack(A, 2)), np.ascontiguousarray(np.stack(B, 2).astype(np.float64)))
    _C.clear(); _C[key] = out; return out
def run(bn, A, B, W0, rid=0, prm=(0., 0., 0.), spd=0.01, lag=2, cap='A', cost=0.003, LO=None, HI=None):
    TQ, DEP, CU, IDL = ii.ref_in(bn); W0 = np.asarray(W0, float)
    if LO is None: LO, HI = aw.bounds(W0, cap)
    return aw._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), A, B,
                    W0, LO, HI, int(rid), np.asarray(prm, float), float(spd), int(lag), float(cost), ii._PP['tax'], ii._D,
                    int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
def cagr(fin, E): return np.maximum(fin, 1e-9) ** (252.0 / E.shape[1]) - 1
def mdd(E): return (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
