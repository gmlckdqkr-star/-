"""Verifier reproduction (a)(b)(c) + delta sensitivity. Data <= 2014-12-31 only (worlds from df5lib; sleeves from clean CSVs cut at load)."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/df6v/repro/nb')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
sys.path.insert(0, '/tmp/df6v/repro')
import df5lib as L
import mysim as M
WARM = 300
ERQ = 0.002 - 0.0055 * (1 - 0.154)
DY3 = (0.025 + 0.015 + 0.040) / 3
CFG = {'c252': dict(V='TQQQ', a=0.20, b=0.00, c=0.80, R=252), 'c63': dict(V='TQQQ', a=0.20, b=0.05, c=0.75, R=63)}
out = {}
DEF3 = M.def3_series()
names = sys.argv[1].split(',') if len(sys.argv) > 1 else ['REAL', 'P', 'X']
deltas = [0.0, 0.005, 0.01]
for wn in names:
    t0 = time.time()
    w = L.world(wn); m = w['m']; ii = w['ii']; idx = w['S'].index
    r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf']); P, T = r.shape
    spx = np.nan_to_num(w['S']['SPX'].values.astype(float)[ii])
    a3 = DEF3.reindex(idx).values.astype(float)
    gaps = int(np.isnan(a3[idx >= DEF3.index.min()]).sum())
    A = a3[ii]; nanfrac = float(np.isnan(A[:, WARM:]).mean()); A = np.nan_to_num(A)
    # cross-check vs source-frame sector columns (world already carries KF sectors)
    s3 = ((w['S']['STAP'] + w['S']['HLTH'] + w['S']['UTIL']) / 3).values.astype(float)
    xchk = float(np.nanmax(np.abs(s3 - DEF3.reindex(idx).values)))
    sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    mA, mS = float(A[sel].mean()), float(spx[sel].mean())
    shN1 = mA - mS
    info = dict(P=P, T=T, yrs=(T - WARM) / 252, gaps=gaps, nanfrac=nanfrac, xchk_vs_S=xchk,
                def3_mean_ann=mA * 252, spx_mean_ann=mS * 252, shiftN1_ann=shN1 * 252,
                def3_vol_ann=float(A[sel].std() * np.sqrt(252)), spx_vol_ann=float(spx[sel].std() * np.sqrt(252)),
                ndx_mean_ann=float(r[sel].mean() * 252), rf_mean_ann=float(rf[sel].mean() * 252))
    QQQ = r - ERQ / 252; TQ = 3 * r - 2 * rf - 0.0245 / 252
    hs = [None] if wn == 'REAL' else [30, 10]
    res = {'info': info}
    for h in hs:
        Th = T if h in (None, 30) else WARM + h * 252
        key = wn if h is None else '%s%d' % (wn, h)
        fq, mq = M.sim(QQQ[:, :, None], np.zeros(1), [1.0], 0, Th=Th); qcg = M.cagr(fq, Th)
        res[key] = {'QQQ': M.summ(qcg, mq)}
        for conv in ['N1', 'N2', 'N1-0.5', 'N1-1.0']:
            if conv == 'N2': sh = 0.0
            elif conv == 'N1': sh = shN1
            else: sh = shN1 + float(conv[3:]) / 100 / 252
            S3 = A - sh - 0.0015 / 252
            for cn, c in CFG.items():
                RET = np.stack([TQ, QQQ, S3], 2); INC = np.array([0.0, 0.0, DY3 / 252])
                f, md = M.sim(RET, INC, [c['a'], c['b'], c['c']], c['R'], Th=Th); cg = M.cagr(f, Th)
                res[key]['%s|%s' % (cn, conv)] = M.summ(cg, md, qcg)
                if h in (None, 30) and conv == 'N1':
                    np.save('/tmp/df6v/repro/arr_%s_%s.npy' % (key, cn), np.stack([cg, md, qcg, mq]))
                del RET
        print(wn, key, 'done %.0fs' % (time.time() - t0), flush=True)
    out[wn] = res
    json.dump(res, open('/tmp/df6v/repro/res_%s.json' % wn, 'w'), indent=1)
    del w, m, r, rf, A, spx, QQQ, TQ
    L._WORLDS.pop(wn, None)
print(json.dumps({k: v['info'] for k, v in out.items()}, indent=1))
