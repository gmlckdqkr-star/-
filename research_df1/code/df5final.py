"""DF5 final: gates -> H1-H4 on passers -> selection (section 5) -> stability, placebo (section 6) -> report rows (section 7).
Writes results/df5_final.json. Run from /tmp/df5w."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5gate as GT, df5stress as ST, df5lib as L, df5data as DD
RES = R.RES; log = R.log; WARM = 300

def select(cands, G, D):
    Q = D['qqq']; rows = D['rows']
    if not cands: return None, None
    sc = {i: G[i]['score'] for i in cands}
    top = max(sc.values()); tied = [i for i in cands if sc[i] >= top - 0.0005]
    ans = max(tied, key=lambda i: G[i]['ddm'])
    alt = max(cands, key=lambda i: (G[i]['ddm'], rows[i]['P30']['cagr']))
    return ans, alt

def stability(cands, ans, arr, D, nrep=1000, seed=11):
    rng = np.random.default_rng(seed); Q = D['qqq']; rows = D['rows']
    qP = arr['QQQ||P30']; qX = arr['QQQ||X30']
    keep = 0; picked = 0
    real_ex = {i: rows[i]['REAL']['cagr'] - Q['REAL']['cagr'] for i in cands}
    for _ in range(nrep):
        ix = rng.integers(0, 500, 500)
        sc = {}; ok = {}
        for i in cands:
            cP = arr['%s||P30' % i]; cX = arr['%s||X30' % i]
            pp = np.median(cP[0][ix] - qP[0][ix]); px = np.median(cX[0][ix] - qX[0][ix])
            sc[i] = min(pp, px, real_ex[i])
            okk = True
            for c, q in ((cP, qP), (cX, qX)):
                cg, md = c[0][ix], c[1][ix]; qcg, qmd = q[0][ix], q[1][ix]
                ddm = 1 - abs(np.percentile(md, 10)) / abs(np.percentile(qmd, 10))
                okk &= bool(np.median(cg - qcg) > 0 and np.median(cg) > np.median(qcg) and np.percentile(cg, 10) >= np.percentile(qcg, 10) and ddm >= 0.1)
            ok[i] = okk
        b = max(sc, key=sc.get); picked += b == ans; keep += ok[ans]
    return dict(selected=picked / nrep, passes_G2G4=keep / nrep)

def placebo(cid, nrep=20, seed=5):
    """circularly shift the decision path (Ltg or W/EV) per path by 252..1260 days inside t >= WARM-1; rerun G1-G5"""
    idx = ST.cfg_index(); c = idx[cid]; rng = np.random.default_rng(seed); passes = 0
    shifts = {}
    res = []
    worlds = {}
    for wname in ('REAL', 'P', 'X'): worlds[wname] = R.W(wname)
    Q = {}
    for wname, X in worlds.items():
        for h in ([None] if wname == 'REAL' else [None, 10]):
            Q[(wname, h)] = R.qqq(X, h)
    for rep in range(nrep):
        ok_all = True
        for wname, X in worlds.items():
            if c['fam'] == 'B' or c['fam'] == 'BV': return dict(note='track B placebo not defined (alarm path inside locked engine)')
            jb = R.job(c, X); P, T = X.P, X.T
            k = rng.integers(252, 1261, P)
            if jb[0] == 'dfe':
                _, m, Lt, kw = jb; Lt2 = Lt.copy()
                for p in range(P): Lt2[p, WARM - 1:] = np.roll(Lt[p, WARM - 1:], k[p])
                jb2 = ('dfe', m, Lt2, kw)
            else:
                _, ids, Wt, EV, kw = jb; W2 = Wt.copy(); E2 = EV.copy()
                for p in range(P):
                    W2[p, WARM - 1:] = np.roll(Wt[p, WARM - 1:], k[p], axis=0); E2[p, WARM - 1:] = np.roll(EV[p, WARM - 1:], k[p]); E2[p, WARM - 1] = True
                jb2 = ('dfk', ids, W2, E2, kw)
            for h in ([None] if wname == 'REAL' else [None, 10]):
                cg, md, _ = R.run_job(jb2, X, h); qcg, qmd, _ = Q[(wname, h)]
                ok_all &= ST.gate_conds(cg, md, qcg, qmd, single=(wname == 'REAL'))
        passes += ok_all; res.append(bool(ok_all))
    return dict(nrep=nrep, pass_rate=passes / nrep)

def main():
    t0 = time.time()
    A, G, D = GT.analyse(); arr = dict(np.load('/tmp/df5w/df5_arr.npz'))
    log('N_raw', A['N_raw'], 'N_unique', A['N_unique'], 'G-pass', len(A['passers']), 'single', A['single'])
    out = dict(analyse={k: v for k, v in A.items()}, H={}, answer=None, alt=None)
    if A['passers']:
        H = ST.stress(A['passers'], G, D); out['H'] = H
        fin = [i for i in A['passers'] if H[i]['all']]
        out['final_passers'] = fin
        ans, alt = select(fin, G, D); out['answer'] = ans; out['alt'] = alt
        if ans:
            out['stability'] = stability(fin, ans, arr, D)
            fams = sorted(set(G[i]['fam'] for i in fin))
            out['placebo'] = {}
            for f in fams:
                b = max([i for i in fin if G[i]['fam'] == f], key=lambda i: G[i]['score'])
                out['placebo'][b] = placebo(b)
    json.dump(out, open(RES + 'df5_final.json', 'w'), indent=1, default=str)
    # report rows: answer, alt, family bests, refs
    ids = [x for x in [out['answer'], out['alt']] if x] + [b['id'] for b in A['best'].values()]
    ids = list(dict.fromkeys(ids))
    rep = ST.report_rows(ids); out['report'] = rep
    json.dump(out, open(RES + 'df5_final.json', 'w'), indent=1, default=str)
    log('saved final %.0fs' % (time.time() - t0))

if __name__ == '__main__':
    main()
