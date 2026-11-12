import sys, json, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import xv1, agree
import t_world; t_world.old()
cfg = json.load(open('/home/user/-/research_xv1/cand/agree.configs.json'))[0]
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(cfg['names'], X.index))
for w in 'XQ':
    S = agree._core(v, w); val = S['valid']; print(w, 'first valid row', int(np.argmax(val)), 'WARM', xv1.WARM, 'all valid after', bool(val[int(np.argmax(val)):].all()))
print(np.isnan(v.ref_target).sum())
