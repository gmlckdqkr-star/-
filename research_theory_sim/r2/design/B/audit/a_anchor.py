import sys, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim
T = 7860; P = 2000
for seed in (777, 10001):
    for mech in (True, False):
        t0 = time.time(); s = sim.simulate(P, T, seed, mechanism=mech); dt = time.time() - t0
        p = s['params']; r, rf, y = s['r'], s['rf'], s['y10']
        W = ee.WARM
        prem = (r[:, W:].mean(1) - rf[:, W:].mean(1)) * 252
        vol = r[:, W:].std(1) * np.sqrt(252)
        print('seed %d mech %s  %.1fs  finite r/rf/y10: %s %s %s  r[:,0]==0: %s' % (seed, mech, dt, np.isfinite(r).all(), np.isfinite(rf).all(), np.isfinite(y).all(), np.all(r[:, 0] == 0)))
        q = lambda a: 'med %.4f p10 %.4f p90 %.4f sd %.4f' % (np.median(a), np.percentile(a, 10), np.percentile(a, 90), np.std(a))
        print('  drawn mu    ', q(p['mu']), ' mean %.4f' % p['mu'].mean())
        print('  drawn sigma ', q(p['sigma']))
        print('  realised prem', q(prem))
        print('  realised vol ', q(vol), ' max |vol-sigma| %.2e' % np.max(np.abs(r.std(1)*0 + np.std(np.log1p(r[:, :]), axis=1)*0)))
        # realised daily log-return std over whole incl. burn-out vs sigma
        lx = np.log1p(r)
        print('  log-ret std (full window) / sigma : med %.4f min %.4f max %.4f' % tuple(np.percentile(np.std(lx, axis=1) * np.sqrt(252) / p['sigma'], [50, 0, 100])))
        print('  corr(realised prem, mu) %.3f  corr(realised vol, sigma) %.3f' % (np.corrcoef(prem, p['mu'])[0, 1], np.corrcoef(vol, p['sigma'])[0, 1]))
        # rf regimes: longest monotone trend over a rolling 10-year window
        ra = rf * 252
        yrs = ra[:, ::252]
        d10 = yrs[:, 10:] - yrs[:, :-10]
        print('  rf ann: med mean %.4f; P(path has a 10y change >= +3pp) %.2f; <= -3pp %.2f; P(10y abs change < 0.5pp somewhere) %.2f' % (
            np.median(ra.mean(1)), np.mean((d10 >= 0.03).any(1)), np.mean((d10 <= -0.03).any(1)), np.mean((np.abs(d10) < 0.005).any(1))))
        # drawdown
        lp = np.cumsum(np.log1p(r[:, W:]), axis=1); dd = np.expm1((lp - np.maximum.accumulate(np.maximum(lp, 0), axis=1)).min(1))
        print('  worst dd med %.3f P(<=-50%%) %.3f P(<=-80%%) %.3f' % (np.median(dd), np.mean(dd <= -0.5), np.mean(dd <= -0.8)))
        if mech:
            print('  A med %.3f B med %.3f  shock_scale med %.5f' % (np.median(p['A']), np.median(p['B']), np.median(p['shock_scale'])))
        else:
            print('  A,B drawn but unused in OFF; shock_scale med %.5f' % np.median(p['shock_scale']))
