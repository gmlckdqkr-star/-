"""Verifier: N3(k_s), N3(k_low), NA(Delta), N4 for the two configs; finer N1-minus-delta grid for the top config; implied k under N1;
split-three-ETF raw variant. Own accounting (mysim). Data <= 2014-12-31."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/df6v/repro/nb')
sys.path.insert(0, '/mnt/project-files/research/df1/code'); sys.path.insert(0, '/tmp/df6v/repro')
import df5lib as L
import mysim as M
WARM = 300
ERQ = 0.002 - 0.0055 * (1 - 0.154)
DY = {'STAP': 0.025, 'HLTH': 0.015, 'UTIL': 0.040}; DY3 = sum(DY.values()) / 3
K = json.load(open('/mnt/project-files/research/df1/results/df6_k.json'))['sleeves']['DEF3']['MKT']
ks, klow, dlt = K['k_all'], K['k_low'], K['delta_ann_all'] / np.sqrt(252)
CFG = {'c252': dict(a=0.20, b=0.00, c=0.80, R=252), 'c63': dict(a=0.20, b=0.05, c=0.75, R=63)}
DEF3 = M.def3_series(); SL = {k: M.load_csv(k) for k in DY}
out = {}
for wn in sys.argv[1].split(','):
    t0 = time.time(); w = L.world(wn); m = w['m']; ii = w['ii']; idx = w['S'].index
    r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf']); P, T = r.shape
    spx = np.nan_to_num(w['S']['SPX'].values.astype(float)[ii])
    A = np.nan_to_num(DEF3.reindex(idx).values.astype(float)[ii])
    sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    rfm = float(rf[sel].mean()); exS = (spx - rf)[sel]; m_ex = float(exS.mean()); s_ex = float(exS.std()); sA = float((A - rf)[sel].std()); mA = float(A[sel].mean())
    tgt = {'N1': rfm + m_ex, 'N3ks': rfm + ks * m_ex / s_ex * sA, 'N3low': rfm + klow * m_ex / s_ex * sA, 'NA': rfm + (m_ex / s_ex + dlt) * sA,
           'N4': rfm + m_ex / s_ex * sA, 'N2': mA}
    for d in (0.25, 0.75, 1.25, 1.5): tgt['N1-%.2f' % d] = rfm + m_ex - d / 100 / 252
    info = dict(k_implied_N1=s_ex / sA, spx_sharpe_ann=m_ex / s_ex * np.sqrt(252), def3_sharpe_raw_ann=(mA - rfm) / sA * np.sqrt(252),
                k_raw=((mA - rfm) / sA) / (m_ex / s_ex), NA_k_equiv=(m_ex / s_ex + dlt) / (m_ex / s_ex),
                mean_vs_N1_pp={k: (v - tgt['N1']) * 252 * 100 for k, v in tgt.items()})
    QQQ = r - ERQ / 252; TQ = 3 * r - 2 * rf - 0.0245 / 252
    hs = {'REAL': {T: 'REAL'}} .get(wn, {T: wn + '30', WARM + 10 * 252: wn + '10'})
    snaps = tuple(h for h in hs if h != T)
    def go(RET, INC, wts, R):
        o = M.sim(RET, INC, wts, R, snaps=snaps)
        res = {T: (o[0], o[1])}
        if snaps: res.update(o[2])
        return {hs[h]: (M.cagr(f, h), md) for h, (f, md) in res.items()}
    Q = go(QQQ[:, :, None], np.zeros(1), [1.0], 0)
    res = {'info': info, 'QQQ': {k: M.summ(*v) for k, v in Q.items()}}
    runs = [(c, cv) for c in CFG for cv in ('N3ks', 'N3low', 'NA', 'N4')] + [('c252', 'N1-%.2f' % d) for d in (0.25, 0.75, 1.25, 1.5)]
    for cn, cv in runs:
        c = CFG[cn]; S3 = A - (mA - tgt[cv]) - 0.0015 / 252
        o = go(np.stack([TQ, QQQ, S3], 2), np.array([0.0, 0.0, DY3 / 252]), [c['a'], c['b'], c['c']], c['R'])
        res['%s|%s' % (cn, cv)] = {k: M.summ(cg, md, Q[k][0]) for k, (cg, md) in o.items()}
    # split three ETFs, raw (N2), annual rebalance, top config weights
    S = [np.nan_to_num(SL[k].reindex(idx).values.astype(float)[ii]) - 0.0015 / 252 for k in ('STAP', 'HLTH', 'UTIL')]
    o = go(np.stack([TQ, QQQ] + S, 2), np.array([0.0, 0.0] + [DY[k] / 252 for k in ('STAP', 'HLTH', 'UTIL')]), [0.2, 0.0, 0.8 / 3, 0.8 / 3, 0.8 / 3], 252)
    res['c252split3|N2'] = {k: M.summ(cg, md, Q[k][0]) for k, (cg, md) in o.items()}
    del S, A, spx, QQQ, TQ, r, rf
    out[wn] = res; json.dump(res, open('/tmp/df6v/repro/conv_%s.json' % wn, 'w'), indent=1)
    L._WORLDS.pop(wn, None); del w, m
    print(wn, 'done %.0fs' % (time.time() - t0), json.dumps(info), flush=True)
