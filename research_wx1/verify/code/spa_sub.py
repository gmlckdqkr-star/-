import numpy as np, time
from spa_mine import spa
W1 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/cache/'
D = np.load(W1+'D.npy', mmap_mode='r'); keep = np.load(W1+'keep.npy')
Dk = np.ascontiguousarray(D[keep]); nz = np.load('nz.npy')
for thr in (60, 120, 240, 400, 540):
    sel = nz >= thr
    res, t, Tu = spa(np.ascontiguousarray(Dk[sel]))
    print('nz>=%d n=%d' % (thr, sel.sum()), res, flush=True)
# the sparse-only part
sel = nz < 60
res, t, Tu = spa(np.ascontiguousarray(Dk[sel])); print('nz<60 n=%d' % sel.sum(), res)
