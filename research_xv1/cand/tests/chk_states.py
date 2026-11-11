import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
cf = {e['name']: xv1.Config(**e) for e in json.load(open('/home/user/-/research_xv1/cand/states.configs.json'))}
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras([], X.index))
B = {n: cf[n].make(v)['B'] for n in ('FCR_P1', 'FCR_P2', 'FCR_P3', 'FCR_P4')}
r = xv1.ref(v)['B']
for n in B: print(n, 'rows differing from FCR_P1', int((B[n] != B['FCR_P1']).sum()), 'rows at 3', int((B[n] != r)[B[n] == 3].sum()))
