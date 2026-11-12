import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
for e in json.load(open('/home/user/-/research_xv1/cand/cross.configs.json')):
    if e['func'] in ('chip_lead', 'soxl_sleeve', 'tmf_fill'):
        c = xv1.Config(**e); X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(c.names, X.index)); W = c.make(v)['Wt']
        print(e['name'], 'nonzero rows in first 300 (engine ignores)', int((W[:300] != 0).any(axis=1).sum()), 'weight at row 299', float(W[299, 0]), 'row 300', float(W[300, 0]))
