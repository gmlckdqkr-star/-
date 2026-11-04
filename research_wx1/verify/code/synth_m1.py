import numpy as np, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/m1/code')
import m1_stats as ST
rng = np.random.default_rng(123)
T = 540
# (1) null calibration: N=3000 correlated rules (factor + idio, t5 innovations, AR(1) 0.1), all mean 0
ps = []; rw = []
t0 = time.time()
for rep in range(150):
    f = rng.standard_t(5, size=(5, T))
    L = rng.normal(size=(3000, 5))
    e = rng.standard_t(5, size=(3000, T))
    D = (L @ f + 1.5*e).astype(np.float32)
    D[:, 1:] += 0.1*D[:, :-1]
    D -= 0.0  # true mean 0
    res, aux = ST.spa_rw(D, verbose=False)
    ps.append(res['p_c']); rw.append(res['rw_n'])
ps = np.array(ps)
print('null: p_c quantiles', np.quantile(ps, [.05, .25, .5, .75, .95]).round(3), 'P(p<.05)=%.3f P(p<.10)=%.3f' % ((ps < .05).mean(), (ps < .10).mean()),
      'RW any reject rate %.3f' % (np.array(rw) > 0).mean(), '%.0fs' % (time.time()-t0), flush=True)
# (2) power: same structure, plant one rule with mean shift giving population t = 3,4,5,6
for tt in (3.0, 4.0, 5.0, 6.0):
    det = []; rwd = []
    for rep in range(40):
        f = rng.standard_t(5, size=(5, T)); L = rng.normal(size=(3000, 5)); e = rng.standard_t(5, size=(3000, T))
        D = (L @ f + 1.5*e).astype(np.float32)
        sd = D[0].std()
        D[0] += tt * sd / np.sqrt(T)
        res, aux = ST.spa_rw(D, verbose=False)
        det.append(res['p_c'] < 0.05); rwd.append(bool(aux['rw_rej'][0]))
    print('planted pop t=%.0f: SPA detect %.2f  RW rejects planted %.2f' % (tt, np.mean(det), np.mean(rwd)), flush=True)
# (3) planted among some negative-mean rules (consistent recentering should help vs upper)
D = np.random.default_rng(5).normal(size=(3000, T)).astype(np.float32)
D[1:2000] -= 0.5   # very poor rules
D[0] += 3.5/np.sqrt(T)
res, aux = ST.spa_rw(D, verbose=False); print('with poor rules: t0=%.2f' % aux['tstat'][0], {k: res[k] for k in ('p_c', 'p_l', 'p_u')})
