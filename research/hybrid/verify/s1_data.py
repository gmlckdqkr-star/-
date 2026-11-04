"""Verifier step 1: load the two real bases, dump raw inputs to npz (scored axis + full axis), basic shape/alignment checks."""
import os, sys, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np, pandas as pd
import hyeng as H, ii, el, sl

OUTD = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/'
NAMES = ['VALPROF4_L1', 'BOND10_L3', 'SPXH_L1', 'BOND10_L1']
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    t0 = time.time()
    c = el.ctx(bn)
    TQ, DEP, CU, IDL = H.ref(bn)
    S, SO = ii.arrays(bn)
    rfull = np.asarray(c['r'])[0]; rf_full = np.asarray(c['rf'])[0]
    I = sl.inputs(np.asarray(c['ii']), c['off'])
    y10 = np.asarray(I['y10'][0]); cape_ok = np.asarray(I['CAPE_OK'][0])
    src = sl.src(); dates_full = np.asarray(src['dates'])[c['off'] + np.asarray(c['ii'])[0]]
    T = TQ.shape[1]
    print(bn, 'TQ', TQ.shape, 'CU', CU.shape, 'S', S.shape, 'r full', rfull.shape, 'WARM', H.WARM, 'T+WARM', T + H.WARM)
    print('  scored dates', dates_full[H.WARM], '..', dates_full[-1], ' full start', dates_full[0])
    # consistency: TQ == 3 r - 2 rf - ER3/252 on the scored axis
    tq2 = 3 * rfull[H.WARM:] - 2 * rf_full[H.WARM:] - el.ER3 / 252
    print('  max|TQ - (3r-2rf-er)| =', float(np.max(np.abs(TQ[0] - tq2))))
    lv = CU[0]; ch = np.sum(lv[1:] != lv[:-1])
    print('  CU levels', np.unique(lv), 'changes', int(ch), 'per yr %.1f' % (ch / (T / 252)))
    cols = {n: S[0, :, H.sid(n)].astype(np.float64) for n in NAMES}
    sos = {n: SO[0, :, H.sid(n)].astype(np.float64) for n in NAMES}
    np.savez(OUTD + 'data_%s.npz' % bn, TQ=TQ[0], DEP=DEP[0], CU=CU[0], rfull=rfull, rf_full=rf_full, y10=y10, cape_ok=cape_ok,
             dates_full=dates_full.astype('datetime64[D]').astype(np.int64), WARM=H.WARM,
             **{'S_' + n: v for n, v in cols.items()}, **{'SO_' + n: v for n, v in sos.items()})
    print('  saved', round(time.time() - t0, 1), 's')

# y10 pre-1962 shape check (interpolated monthly values would show piecewise-constant daily differences)
src = sl.src(); d = pd.DatetimeIndex(src['dates']); y = np.asarray(src['y10'])
for a, b in [('1955-01-01', '1961-12-31'), ('1962-01-01', '1970-12-31'), ('1986-01-01', '1990-12-31')]:
    m = (d >= a) & (d <= b); yy = y[m]; dd = np.diff(yy)
    nz = np.mean(np.abs(dd) > 1e-12)
    # fraction of days whose difference equals the previous day's difference (linear interpolation signature)
    same = np.mean(np.abs(dd[1:] - dd[:-1]) < 1e-12)
    print('y10 %s..%s: frac nonzero daily change %.3f, frac equal consecutive change %.3f' % (a, b, nz, same))
