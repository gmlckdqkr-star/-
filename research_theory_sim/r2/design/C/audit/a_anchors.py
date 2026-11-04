"""AUDIT (lane C): anchors (brief 2b-2d) and simulator sanity (ON/OFF), from sim.py on 2000 paths. Synthetic only."""
import sys, os, json, time
TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOP); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import numpy as np, sim, exec_engine as ee
T = 300 + 30 * 252; W = ee.WARM; DPY = 252
q = lambda v: '%.4f [p10 %.4f, p90 %.4f]' % (np.median(v), np.percentile(v, 10), np.percentile(v, 90))
seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
out = {}
S = {}
for mech in (True, False):
    t0 = time.time(); s = sim.simulate(2000, T, seed, mechanism=mech); S[mech] = s
    r, rf, y10 = s['r'], s['rf'], s['y10']; p = s['params']
    tag = 'ON' if mech else 'OFF'
    print('--- seed %d %s  sim %.0fs' % (seed, tag, time.time() - t0), flush=True)
    print('  finite r/rf/y10: %s %s %s ; r[:,0]==0: %s ; min r %.4f max r %.4f ; rf/yr range [%.4f, %.4f]; y10 range [%.2f, %.2f]' % (
        np.isfinite(r).all(), np.isfinite(rf).all(), np.isfinite(y10).all(), bool((r[:, 0] == 0).all()), r.min(), r.max(),
        rf.min() * DPY, rf.max() * DPY, y10.min(), y10.max()))
    print('  drawn pi_bar   :', q(p['pi_bar']), ' mean %.4f sd %.4f' % (p['pi_bar'].mean(), p['pi_bar'].std()))
    print('  drawn sigma_bar:', q(p['sigma_bar']), ' log-sd %.3f' % np.log(p['sigma_bar']).std())
    rr, ff = r[:, W:], rf[:, W:]
    prem = (rr - ff).mean(axis=1) * DPY; vol = rr.std(axis=1) * np.sqrt(DPY)
    ex = rr - ff
    print('  realised arith excess/yr:', q(prem), ' pooled mean %.4f (vs mean drawn pi_bar %.4f)' % (prem.mean(), p['pi_bar'].mean()))
    print('  realised vol/yr         :', q(vol), ' corr(realised vol, sigma_bar) %.3f' % np.corrcoef(vol, p['sigma_bar'])[0, 1])
    print('  realised prem - pi_bar  :', q(prem - p['pi_bar']), ' realised vol/sigma_bar', q(vol / p['sigma_bar']))
    lp = np.cumsum(np.log1p(rr), axis=1)
    mdd = np.expm1((lp - np.maximum.accumulate(np.maximum(lp, 0), axis=1)).min(axis=1))
    print('  worst drawdown (price):', q(mdd), ' P(<=-50%%) %.3f' % np.mean(mdd <= -0.5))
    a = np.abs(ex) - np.abs(ex).mean(axis=1, keepdims=True)
    ac = {k: float(np.mean((a[:, k:] * a[:, :-k]).mean(axis=1) / a.var(axis=1))) for k in (1, 5, 20, 60)}
    # 1-year-ahead predictability: corr of trailing 250d realised var ratio with next 250d excess return
    yr = np.add.reduceat(ex, np.arange(0, ex.shape[1], 252), axis=1)[:, :30]
    vv = np.add.reduceat(ex ** 2, np.arange(0, ex.shape[1], 252), axis=1)[:, :30]
    z = np.log(vv[:, :-1] / vv.mean(axis=1, keepdims=True)); fwd = yr[:, 1:] - yr[:, 1:].mean(axis=1, keepdims=True)
    print('  |excess| autocorr lags 1/5/20/60: %s ; corr(log var_yr, next-yr excess) %.3f' % (
        ' '.join('%.3f' % ac[k] for k in ac), np.corrcoef(z.ravel(), fwd.ravel())[0, 1]))
    out[tag] = dict(pi_med=float(np.median(p['pi_bar'])), sig_med=float(np.median(p['sigma_bar'])), prem_med=float(np.median(prem)),
                    vol_med=float(np.median(vol)), prem_mean=float(prem.mean()), mdd_med=float(np.median(mdd)), ac=ac)
    del lp, a, ex, rr, ff
print('same drawn params ON/OFF:', all(np.array_equal(S[True]['params'][k], S[False]['params'][k]) for k in ('pi_bar', 'sigma_bar', 'jshare', 'Ybar', 'kY', 'lam_bar')),
      '| same rf/y10 paths ON/OFF:', np.array_equal(S[True]['rf'], S[False]['rf']), np.array_equal(S[True]['y10'], S[False]['y10']))
# rates (2d): long trending regimes
rf = S[True]['rf'] * DPY; P = rf.shape[0]
ann = rf[:, ::DPY]                                   # yearly samples (31 per path)
best_up = np.zeros(P); best_dn = np.zeros(P); stable10 = np.zeros(P, bool)
for i in range(ann.shape[1] - 10):
    d10 = ann[:, i + 10] - ann[:, i]
    seg = ann[:, i:i + 11]; tt = np.arange(11) - 5.0
    sl = (seg * tt).sum(1) / (tt ** 2).sum(); res = seg - seg.mean(1, keepdims=True) - sl[:, None] * tt
    r2 = 1 - (res ** 2).sum(1) / np.maximum(((seg - seg.mean(1, keepdims=True)) ** 2).sum(1), 1e-12)
    up = (sl * 10 >= 0.03) & (r2 >= 0.7); dn = (sl * 10 <= -0.03) & (r2 >= 0.7)
    best_up = np.maximum(best_up, np.where(up, sl * 10, 0)); best_dn = np.minimum(best_dn, np.where(dn, sl * 10, 0))
    stable10 |= (seg.max(1) - seg.min(1)) < 0.015
print('rates: share of paths with a 10-yr steady uptrend >= 3pp (fit R2>=0.7): %.3f ; downtrend: %.3f ; either: %.3f ; 10-yr stable band <1.5pp: %.3f' % (
    np.mean(best_up > 0), np.mean(best_dn < 0), np.mean((best_up > 0) | (best_dn < 0)), stable10.mean()))
print('rates: monthly-step share %.3f ; rf/yr median %.4f p5 %.4f p95 %.4f' % (
    S[True]['params']['monthly_rates'].mean(), np.median(rf), np.percentile(rf, 5), np.percentile(rf, 95)))
if seed == 1:   # does the current sim.py reproduce the designer's earliest logged baselines (11:00Z, before the 11:21 sim edit)?
    for mech, logged in ((True, 0.01242 + 0.04250), (False, 0.03249 + 0.02174)):
        s2 = sim.simulate(500, T, 2, mechanism=mech)
        r = np.concatenate([S[mech]['r'][:500], s2['r']]); f = np.concatenate([S[mech]['rf'][:500], s2['rf']])
        h = ee.summary(ee.hold(r, f, 1))['cagr_med']
        print('E1 baseline hold1 seeds 1-2 %s: now %.5f, implied by variants.csv row of 11:00Z %.5f' % ('ON' if mech else 'OFF', h, logged))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anchors_seed%d.json' % seed), 'w'), indent=1)
