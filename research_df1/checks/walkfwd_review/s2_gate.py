"""Reviewer: re-evaluate walkfwd's DF2 adoption gate (a) with the PRECOMMIT text reading (bond-excess-0 shift = mean(rb-rf) over the
pool's SOURCE period, audit F1) instead of the path-day mean walkfwd uses. <=2014 only; pools NON-ACTUAL bootstrap.
Usage: python -B s2_gate.py [seed ...]"""
import sys, os, json, time, numpy as np
sys.path.insert(0, '/tmp/chk_walkfwd'); sys.path.insert(0, '/mnt/project-files/research/df1/code')
import walkfwd as WF, dfe, run_df2 as R2, jp
W = dfe.WARM; C = WF.C; IDS = WF.IDS; ISDF2 = WF.ISDF2
CA = '/tmp/chk_walkfwd/cache/'
L = lambda f: dict(np.load(CA + f + '.npz'))
spx = L('spx2954'); RL = {'A': L('real_A'), 'B': L('real_B')}
EXS = {}
for p, (a, b) in WF.PER.items():
    X = jp.mkX(*jp.calendar(a, b), 'NDX'); assert X.index.max() <= np.datetime64('2014-12-31')
    EXS[p] = float(np.mean(X['rb'].values[1:] - X['rf'].values[1:]))
print('source-period excess/day', EXS, {k: v * 252 for k, v in EXS.items()}, flush=True)
def sel(pl, rl, bud, mask=None):
    wd = np.minimum(np.minimum(pl['mdd_p10'], rl['mdd']), spx['mdd']); ok = wd >= bud
    if mask is not None: ok &= mask
    ins = np.where(ok)[0]
    if not len(ins): return None
    bv = pl['cagr'][ins].max(); tie = ins[bv - pl['cagr'][ins] < 0.0005]; return int(tie[np.argmax(rl['cagr'][tie])])
def med(cfg, m, **kw): return float(np.median(dfe.stats(R2.run_cfg(cfg, m, **kw), m['r'].shape[1])[0]))
out = dict(ex_src=EXS, rows=[])
seeds = [int(s) for s in sys.argv[1:]] or [7, 23, 41, 59, 101]
t0 = time.time()
for seed in seeds:
    for s, t in (('A', 'B'), ('B', 'A')):
        m = WF.pool(s, seed); PLs = L('pool_%s_s%d' % (s, seed)); PLt = L('pool_%s_s%d' % (t, seed))
        exp = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:]))
        m_p = dict(m); m_p['rb'] = m['rb'] - exp; m_s = dict(m); m_s['rb'] = m['rb'] - EXS[s]
        for tn, bud in (('T25', -.25), ('T30', -.30), ('T40', -.40)):
            u = sel(PLs, RL[s], bud); d = sel(PLs, RL[s], bud, ~ISDF2)
            if u is None or not ISDF2[u]: continue
            g = dict(seed=seed, dir=s + '2' + t, tier=tn, union=IDS[u], df1=IDS[d], ex_path=exp, ex_src=EXS[s])
            g['u_bx0_path'] = med(C[u], m_p); g['d_bx0_path'] = med(C[d], m_p)
            g['u_bx0_src'] = med(C[u], m_s); g['d_bx0_src'] = med(C[d], m_s)
            g['u_c2'] = med(C[u], m, cost=0.006); g['d_c2'] = med(C[d], m, cost=0.006)
            g['adopt_path'] = IDS[u] if (g['u_bx0_path'] > g['d_bx0_path'] and g['u_c2'] > g['d_c2']) else IDS[d]
            g['adopt_src'] = IDS[u] if (g['u_bx0_src'] > g['d_bx0_src'] and g['u_c2'] > g['d_c2']) else IDS[d]
            j = IDS.index(g['adopt_src'])
            g['src_pick_oot'] = dict(real_cagr=float(RL[t]['cagr'][j]), real_mdd=float(RL[t]['mdd'][j]), pool_cagr=float(PLt['cagr'][j]), pool_mdd_p10=float(PLt['mdd_p10'][j]))
            out['rows'].append(g)
            print('%3d %s %s union %-30s df1 %-22s | ex path %.3e src %.3e | bx0 path %.4f vs %.4f  src %.4f vs %.4f | c2 %.4f vs %.4f | adopt path %s src %s | srcpick OOT real %.4f/%.4f pool %.4f/%.4f  %.0fs' % (
                seed, g['dir'], tn, g['union'], g['df1'], exp, EXS[s], g['u_bx0_path'], g['d_bx0_path'], g['u_bx0_src'], g['d_bx0_src'], g['u_c2'], g['d_c2'],
                g['adopt_path'], g['adopt_src'], *g['src_pick_oot'].values(), time.time() - t0), flush=True)
        del m, m_p, m_s
json.dump(out, open('/tmp/rev_walkfwd/gate_src.json', 'w'), indent=1)
