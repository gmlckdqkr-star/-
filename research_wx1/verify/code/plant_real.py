import numpy as np, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/m1/code')
import m1_stats as ST
W1 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/cache/'
D = np.load(W1+'D.npy', mmap_mode='r'); keep = np.load(W1+'keep.npy')
Dk = np.ascontiguousarray(D[keep]); Dk -= Dk.mean(1, keepdims=True)      # every rule: true mean 0 (in-sample)
j = 1361   # a full-activity real rule as the carrier of the planted edge
base = Dk[j].copy()
# its bootstrap se (same W as worker)
W = ST.stationary_counts(Dk.shape[1]); se = (W @ base / Dk.shape[1]).std()
for k in (4.0, 5.0, 5.5, 6.0, 7.0):
    Dk[j] = base + k*se
    t0 = time.time(); res, aux = ST.spa_rw(Dk, verbose=False)
    print('planted t=%.1f: tstat %.2f SPA p_c %.3f p_u %.3f RW crit %.2f rejects planted %s, rw_n %d (%.0fs)' % (
        k, aux['tstat'][j], res['p_c'], res['p_u'], res['rw_crit'][0], aux['rw_rej'][j], res['rw_n'], time.time()-t0), flush=True)
