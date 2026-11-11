import sys, json, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import xv1
cfgs = json.load(open('/home/user/-/research_xv1/cand/agree.configs.json'))
for e in cfgs:
    cfg = xv1.Config(**e)
    X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(cfg.names, X.index))
    m = xv1._call(cfg.make, v); ref = xv1.ref(v)
    nB = int((m['B'] != ref['B']).sum()); W = m['Wt']; nz = int((W != 0).any(axis=1).sum()); chg = int((W[1:] != W[:-1]).any(axis=1).sum())
    ep = int(((W != 0).any(axis=1)[1:] & ~(W != 0).any(axis=1)[:-1]).sum())
    # first row where the candidate differs from v1 (row index; first account row = WARM)
    diff = (m['B'] != ref['B']) | (W != 0).any(axis=1); first = int(np.argmax(diff)) if diff.any() else -1
    pt = xv1.prefix_test(cfg.make, cfg.names, end=xv1.OLD_END, n_rand=25)
    print(e['name'], 'rowsBdiff', nB, 'rowsW!=0', nz, 'Wchanges', chg, 'episodes', ep, 'first_diff_row', first, 'WARM', xv1.WARM, pt, flush=True)
